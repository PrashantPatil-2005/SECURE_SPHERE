-- runtime.lua — per-worker cached view over the waf_config shared dict.
-- Re-parses JSON lists when the version counter is bumped by waf_config.load().

local cjson    = require("cjson.safe")
local iputils  = require("iputils")

local M = {}

local cache = {
    version        = -1,
    allowlist      = {},
    blocklist      = {},
    geo_countries  = {},
    geo_enabled    = false,
    captcha_enabled= false,
    tls_enabled    = false,
    upstream       = "",
    enabled        = false,
    rpm            = 600,
    captcha_secret = "",
}

local function rebuild()
    local cfg = ngx.shared.waf_config
    local v = cfg:get("version") or 0
    if v == cache.version then return cache end

    cache.version        = v
    cache.enabled        = cfg:get("enabled") == 1
    cache.upstream       = cfg:get("upstream") or ""
    cache.rpm            = cfg:get("rpm") or 600
    cache.geo_enabled    = cfg:get("geo_enabled") == 1
    cache.captcha_enabled= cfg:get("captcha_enabled") == 1
    cache.tls_enabled    = cfg:get("tls_enabled") == 1
    cache.captcha_secret = cfg:get("captcha_secret") or ""

    local allow_raw = cfg:get("ip_allowlist") or "[]"
    local block_raw = cfg:get("ip_blocklist") or "[]"
    local geo_raw   = cfg:get("geo_blocklist") or "[]"

    cache.allowlist = iputils.parse_list(cjson.decode(allow_raw) or {})
    cache.blocklist = iputils.parse_list(cjson.decode(block_raw) or {})

    local countries = {}
    for _, cc in ipairs(cjson.decode(geo_raw) or {}) do
        if type(cc) == "string" and #cc == 2 then
            countries[cc:upper()] = true
        end
    end
    cache.geo_countries = countries

    return cache
end

function M.get() return rebuild() end

return M
