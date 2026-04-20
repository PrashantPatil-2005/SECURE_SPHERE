-- geoip.lua — country code resolver.
--
-- Strategy: trust CDN-injected headers when present (production-common
-- pattern: SecuriSphere sits behind Cloudflare / CloudFront / Fastly,
-- which enrich requests with a 2-letter ISO country code).
--
-- Headers checked, in priority order:
--   CF-IPCountry              (Cloudflare)
--   CloudFront-Viewer-Country (AWS CloudFront)
--   X-Country-Code            (generic, e.g. Fastly / custom edge)
--
-- Returns uppercase 2-letter code or nil.

local M = {}

local function header(name)
    local v = ngx.req.get_headers()[name]
    if type(v) == "table" then v = v[1] end
    if type(v) == "string" and #v == 2 then return v:upper() end
    return nil
end

function M.country()
    return header("CF-IPCountry")
        or header("CloudFront-Viewer-Country")
        or header("X-Country-Code")
end

return M
