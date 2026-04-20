-- captcha.lua — tiny Proof-of-Work challenge served inline.
-- On challenge: issue nonce + target-difficulty. Client computes sha256(nonce..n)
-- with N leading hex zeros, POSTs result; we verify and set a signed cookie.

local cjson = require("cjson.safe")
local sha   = require("resty.sha256")
local str   = require("resty.string")

local M = {}

local COOKIE_NAME = "sp_pow"
local DIFFICULTY  = 4      -- 4 hex zeros ≈ 2^16 hashes, sub-second on browsers
local TTL_SEC     = 3600

local function b64url(s)
    return (ngx.encode_base64(s):gsub("+","-"):gsub("/","_"):gsub("=",""))
end

local function hmac(secret, msg)
    return ngx.hmac_sha1(secret, msg)
end

local function sign(secret, payload)
    return b64url(payload) .. "." .. b64url(hmac(secret, payload))
end

local function verify(secret, token)
    if not token or token == "" then return false end
    local p64, sig = token:match("^([^.]+)%.([^.]+)$")
    if not p64 then return false end
    -- decode base64url
    local pad = #p64 % 4
    local norm = p64:gsub("-","+"):gsub("_","/") .. string.rep("=", pad == 0 and 0 or 4-pad)
    local payload = ngx.decode_base64(norm)
    if not payload then return false end
    local exp = tonumber(payload:match("^(%d+):"))
    if not exp or exp < ngx.time() then return false end
    local expected = b64url(hmac(secret, payload))
    if sig ~= expected then return false end
    return true
end

function M.is_passed(secret)
    local cookies = ngx.var.http_cookie or ""
    local tok = cookies:match(COOKIE_NAME .. "=([^;%s]+)")
    return verify(secret, tok)
end

local function sha256hex(s)
    local h = sha:new()
    h:update(s)
    return str.to_hex(h:final())
end

local CHALLENGE_HTML = [[
<!doctype html><html><head><meta charset="utf-8"><title>Verifying…</title>
<style>
body{background:#0a0a0a;color:#eab308;font-family:ui-monospace,monospace;padding:40px;text-align:center}
.box{max-width:520px;margin:40px auto;border:1px solid #334155;border-radius:12px;padding:28px;background:#0f172a}
h2{color:#fbbf24;margin-top:0}
.bar{height:6px;background:#1e293b;border-radius:99px;overflow:hidden;margin:16px 0}
.fill{height:100%;background:linear-gradient(90deg,#eab308,#f97316);width:0%;transition:width .2s}
small{color:#64748b}
</style></head><body>
<div class="box">
<h2>SecuriSphere — verifying your browser</h2>
<p id="msg">Running proof-of-work challenge…</p>
<div class="bar"><div id="f" class="fill"></div></div>
<small>Difficulty: __DIFF__ hex zeros. No JavaScript = no access.</small>
</div>
<script>
(async function(){
  const nonce="__NONCE__", diff=__DIFF__, enc=new TextEncoder();
  const target="0".repeat(diff);
  const msg=document.getElementById("msg"), f=document.getElementById("f");
  let i=0, t0=performance.now();
  while(true){
    const buf=await crypto.subtle.digest("SHA-256", enc.encode(nonce+":"+i));
    const hex=[...new Uint8Array(buf)].map(b=>b.toString(16).padStart(2,"0")).join("");
    if(hex.startsWith(target)) break;
    i++;
    if(i%500===0){ f.style.width=Math.min(100,(i/65536)*100)+"%"; await new Promise(r=>setTimeout(r,0)); }
  }
  f.style.width="100%";
  msg.textContent="Verified in "+((performance.now()-t0)/1000).toFixed(1)+"s. Reloading…";
  const r=await fetch("/__sp_captcha_verify",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({nonce:nonce,n:i})});
  if(r.ok){ location.reload(); } else { msg.textContent="Verification failed."; }
})();
</script></body></html>
]]

function M.serve_challenge(secret)
    local nonce = sha256hex(tostring(ngx.now()) .. ngx.var.remote_addr .. secret):sub(1, 24)
    -- Stash (nonce, exp) by signing with secret so verify can validate without server state
    local exp   = ngx.time() + 120
    local stash = sign(secret, ("c:%d:%s"):format(exp, nonce))
    ngx.header["Set-Cookie"] = ("sp_pow_c=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=120"):format(stash)
    ngx.header.content_type  = "text/html"
    ngx.status = 429
    local html = CHALLENGE_HTML:gsub("__NONCE__", nonce):gsub("__DIFF__", tostring(DIFFICULTY))
    ngx.say(html)
    return ngx.exit(429)
end

function M.handle_verify(secret)
    ngx.req.read_body()
    local body = ngx.req.get_body_data() or "{}"
    local j = cjson.decode(body) or {}
    local n = tonumber(j.n)
    local nonce = j.nonce or ""
    if not n or nonce == "" then return ngx.exit(400) end

    local cookies = ngx.var.http_cookie or ""
    local stash = cookies:match("sp_pow_c=([^;%s]+)")
    if not stash then return ngx.exit(400) end
    local p64, sig = stash:match("^([^.]+)%.([^.]+)$")
    if not p64 then return ngx.exit(400) end
    local pad = #p64 % 4
    local norm = p64:gsub("-","+"):gsub("_","/") .. string.rep("=", pad == 0 and 0 or 4-pad)
    local payload = ngx.decode_base64(norm) or ""
    if sig ~= b64url(hmac(secret, payload)) then return ngx.exit(403) end
    local exp, want = payload:match("^c:(%d+):(.+)$")
    if not exp or tonumber(exp) < ngx.time() or want ~= nonce then return ngx.exit(403) end

    local h = sha256hex(nonce .. ":" .. tostring(n))
    if h:sub(1, DIFFICULTY) ~= string.rep("0", DIFFICULTY) then
        return ngx.exit(403)
    end

    local token_payload = ("%d:%s"):format(ngx.time() + TTL_SEC, ngx.var.remote_addr or "?")
    local tok = sign(secret, token_payload)
    ngx.header["Set-Cookie"] = {
        ("sp_pow=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d"):format(tok, TTL_SEC),
        "sp_pow_c=; Path=/; Max-Age=0",
    }
    ngx.header.content_type = "application/json"
    ngx.say('{"ok":true}')
    return ngx.exit(200)
end

return M
