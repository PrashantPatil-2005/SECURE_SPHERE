-- log_by_lua: push every request (and especially blocks) to Redis list events:proxy
local cjson = require("cjson.safe")
local redis = require("resty.redis")

local REDIS_HOST = os.getenv("REDIS_HOST") or "redis"
local REDIS_PORT = tonumber(os.getenv("REDIS_PORT") or "6379")

-- Sample allow-pass requests at 10% to keep volume low; always log blocks.
local blocked = ngx.var.waf_blocked == "1"
if not blocked and math.random() > 0.10 then return end

local record = {
    ts         = ngx.var.time_iso8601,
    remote     = ngx.var.remote_addr,
    method     = ngx.var.request_method,
    uri        = ngx.var.request_uri,
    status     = tonumber(ngx.var.status) or 0,
    ua         = ngx.var.http_user_agent,
    referer    = ngx.var.http_referer,
    host       = ngx.var.host,
    blocked    = blocked,
    rule       = ngx.var.waf_rule,
    upstream   = ngx.shared.waf_config:get("upstream") or "",
}

local body = cjson.encode(record)
if not body then return end

local r = redis:new()
r:set_timeout(250)
local ok, err = r:connect(REDIS_HOST, REDIS_PORT)
if not ok then
    ngx.log(ngx.WARN, "redis connect: ", err)
    return
end

r:lpush("events:proxy", body)
r:ltrim("events:proxy", 0, 4999)
r:set_keepalive(10000, 50)
