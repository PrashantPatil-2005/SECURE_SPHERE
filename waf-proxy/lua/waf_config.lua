-- Loads runtime config from /etc/waf/conf.d/runtime.json into shared dict.
-- Backend writes this file via shared docker volume, then calls /waf/reload.

local cjson = require("cjson.safe")
local M = {}

local CONFIG_PATH = "/etc/waf/conf.d/runtime.json"

local function encode_list(arr)
    if type(arr) ~= "table" then return "[]" end
    return cjson.encode(arr) or "[]"
end

function M.load()
    local f = io.open(CONFIG_PATH, "r")
    local cfg = {}
    if f then
        local body = f:read("*a")
        f:close()
        cfg = cjson.decode(body or "{}") or {}
    end

    local d = ngx.shared.waf_config
    d:set("upstream",        cfg.upstream or "")
    d:set("enabled",         cfg.waf_enabled and 1 or 0)
    d:set("rpm",             tonumber(cfg.rate_limit_rpm) or 600)
    d:set("tls_enabled",     cfg.tls_enabled and 1 or 0)
    d:set("captcha_enabled", cfg.captcha_enabled and 1 or 0)
    d:set("geo_enabled",     cfg.geo_enabled and 1 or 0)
    d:set("ip_allowlist",    encode_list(cfg.ip_allowlist))
    d:set("ip_blocklist",    encode_list(cfg.ip_blocklist))
    d:set("geo_blocklist",   encode_list(cfg.geo_blocklist))
    if cfg.captcha_secret and cfg.captcha_secret ~= "" then
        d:set("captcha_secret", cfg.captcha_secret)
    elseif not d:get("captcha_secret") then
        -- generate once, persist in dict only (not file) — backend can overwrite
        d:set("captcha_secret", tostring(ngx.now()) .. tostring(math.random(1e9)))
    end

    -- bump version so per-worker caches rebuild
    local v = d:get("version") or 0
    d:set("version", v + 1)
end

return M
