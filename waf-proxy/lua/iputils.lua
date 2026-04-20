-- iputils.lua — IPv4 CIDR parsing + membership check using shared-dict lookup.
-- Keeps parsed ranges in a table; designed to be rebuilt on each config reload.

local M = {}

local function ip2num(ip)
    if not ip then return nil end
    local a, b, c, d = ip:match("^(%d+)%.(%d+)%.(%d+)%.(%d+)$")
    if not a then return nil end
    a, b, c, d = tonumber(a), tonumber(b), tonumber(c), tonumber(d)
    if not (a and b and c and d) then return nil end
    if a > 255 or b > 255 or c > 255 or d > 255 then return nil end
    return a * 16777216 + b * 65536 + c * 256 + d
end
M.ip2num = ip2num

-- parse_cidr("10.0.0.0/8") -> {lo=..., hi=...}
local function parse_cidr(s)
    if not s or s == "" then return nil end
    s = s:gsub("%s+", "")
    local ip, bits = s:match("^(.-)/(%d+)$")
    if not ip then
        ip, bits = s, 32
    else
        bits = tonumber(bits)
        if not bits or bits < 0 or bits > 32 then return nil end
    end
    local n = ip2num(ip)
    if not n then return nil end
    local mask
    if bits == 0 then
        mask = 0
    else
        mask = ((2 ^ bits) - 1) * (2 ^ (32 - bits))
    end
    local lo = n - (n % (2 ^ (32 - bits)))
    local hi = lo + (2 ^ (32 - bits)) - 1
    return { lo = lo, hi = hi, mask = mask }
end
M.parse_cidr = parse_cidr

function M.parse_list(arr)
    local out = {}
    if type(arr) ~= "table" then return out end
    for _, s in ipairs(arr) do
        local r = parse_cidr(s)
        if r then out[#out + 1] = r end
    end
    return out
end

function M.contains(ranges, ip)
    local n = ip2num(ip)
    if not n or not ranges then return false end
    for i = 1, #ranges do
        local r = ranges[i]
        if n >= r.lo and n <= r.hi then return true end
    end
    return false
end

return M
