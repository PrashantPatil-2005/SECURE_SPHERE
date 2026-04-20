-- access_by_lua: inspect request, enforce policy layers in order:
--   1. IP blocklist     → 403
--   2. IP allowlist     → bypass all further checks (trusted)
--   3. Geo blocklist    → 403 (uses CDN country header)
--   4. CAPTCHA gate     → serve PoW challenge if enabled & cookie missing
--   5. Rate limit       → 429 (or captcha challenge if captcha_enabled)
--   6. Signature rules  → 403
local cjson   = require("cjson.safe")
local runtime = require("runtime")
local iputils = require("iputils")
local captcha = require("captcha")
local geoip   = require("geoip")

local stats = ngx.shared.waf_stats
local rl    = ngx.shared.waf_ratelimit

stats:incr("requests", 1, 0)

local rt = runtime.get()
if not rt.enabled then return end

-- Handle captcha verify submission before any policy check
if ngx.var.uri == "/__sp_captcha_verify" and ngx.req.get_method() == "POST" then
    return captcha.handle_verify(rt.captcha_secret)
end

local client_ip = ngx.var.remote_addr or "?"

-- ── 1. IP blocklist ──────────────────────────────────────────────────────
if iputils.contains(rt.blocklist, client_ip) then
    ngx.var.waf_blocked = "1"
    ngx.var.waf_rule    = "ip_block"
    stats:incr("blocked", 1, 0)
    ngx.status = 403
    ngx.header.content_type = "application/json"
    ngx.say('{"blocked":true,"rule":"ip_block"}')
    return ngx.exit(403)
end

-- ── 2. IP allowlist (bypass all checks) ──────────────────────────────────
local allow_bypass = iputils.contains(rt.allowlist, client_ip)

if not allow_bypass then
    -- ── 3. Geo blocklist ─────────────────────────────────────────────────
    if rt.geo_enabled and next(rt.geo_countries) then
        local cc = geoip.country()
        if cc and rt.geo_countries[cc] then
            ngx.var.waf_blocked = "1"
            ngx.var.waf_rule    = "geo_block"
            stats:incr("blocked", 1, 0)
            ngx.status = 403
            ngx.header.content_type = "application/json"
            ngx.say(cjson.encode({ blocked = true, rule = "geo_block", country = cc }))
            return ngx.exit(403)
        end
    end

    -- ── 4. CAPTCHA gate ──────────────────────────────────────────────────
    local captcha_passed = false
    if rt.captcha_enabled then
        captcha_passed = captcha.is_passed(rt.captcha_secret)
    end

    -- ── 5. Rate limit ────────────────────────────────────────────────────
    local rkey = "rl:" .. client_ip
    local cnt  = rl:incr(rkey, 1, 0, 60)
    if cnt and cnt > rt.rpm then
        ngx.var.waf_blocked = "1"
        ngx.var.waf_rule    = "rate_limit"
        stats:incr("blocked", 1, 0)
        stats:incr("ratelimit", 1, 0)
        if rt.captcha_enabled and not captcha_passed then
            -- offer PoW instead of hard block
            return captcha.serve_challenge(rt.captcha_secret)
        end
        ngx.status = 429
        ngx.header["Retry-After"] = "60"
        ngx.say('{"blocked":true,"rule":"rate_limit","rpm":', rt.rpm, '}')
        return ngx.exit(429)
    end

    -- If captcha required globally and user hasn't passed, challenge now.
    -- (Opt-in: only when a special header/cookie demands. We leave global
    -- captcha off by default — it only triggers on rate_limit above.)
end

-- ── 6. Signature rules ───────────────────────────────────────────────────
local uri    = ngx.var.request_uri or ""
local ua     = ngx.var.http_user_agent or ""
local ref    = ngx.var.http_referer or ""
local method = ngx.var.request_method or ""

local body = ""
if method == "POST" or method == "PUT" or method == "PATCH" then
    ngx.req.read_body()
    body = ngx.req.get_body_data() or ""
    if #body > 32768 then body = body:sub(1, 32768) end
end

local haystack = (uri .. " " .. ua .. " " .. ref .. " " .. body):lower()

local rules = {
    { name = "sqli",     counter = "sqli",
      patterns = {
          "union[%s%+]+select", "select[%s%+]+.*[%s%+]+from",
          "'%s*or%s*'1'%s*=%s*'1", "'%s*or%s*1=1", "sleep%(%d+%)",
          "benchmark%(", "load_file%(", "into%s+outfile", "xp_cmdshell",
          "information_schema", "0x27%s*or%s*1=1", "'%-%-"
      } },
    { name = "xss",      counter = "xss",
      patterns = {
          "<script[^>]*>", "javascript:", "onerror%s*=", "onload%s*=",
          "onclick%s*=", "<iframe", "<svg[^>]*onload", "document%.cookie",
          "eval%(", "alert%("
      } },
    { name = "traversal",counter = "traversal",
      patterns = {
          "%.%./", "%.%.%%2f", "%.%.%%5c",
          "/etc/passwd", "/etc/shadow", "c:[/\\]windows[/\\]", "boot%.ini",
          "/proc/self/environ"
      } },
    { name = "cmd_inj",  counter = "sqli",
      patterns = {
          ";%s*cat%s+", "`cat%s+", "%$%(cat%s+", "wget%s+http",
          "curl%s+http", "nc%s+%-e", "bash%s+%-i", "/bin/sh"
      } },
    { name = "scanner",  counter = "blocked",
      patterns = {
          "sqlmap", "nikto", "nmap", "acunetix", "nessus", "burpsuite",
          "w3af", "dirbuster", "gobuster", "ffuf"
      } },
}

if not allow_bypass then
    for _, r in ipairs(rules) do
        for _, p in ipairs(r.patterns) do
            if haystack:find(p) then
                ngx.var.waf_blocked = "1"
                ngx.var.waf_rule    = r.name
                stats:incr("blocked", 1, 0)
                if r.counter then stats:incr(r.counter, 1, 0) end
                ngx.status = 403
                ngx.header.content_type = "application/json"
                ngx.say(cjson.encode({
                    blocked = true,
                    rule = r.name,
                    pattern = p,
                    msg = "Request blocked by SecuriSphere WAF",
                }))
                return ngx.exit(403)
            end
        end
    end
end
