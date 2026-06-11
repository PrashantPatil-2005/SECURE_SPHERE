"""
SecuriSphere — Configuration routes
===================================
WAF / reverse-proxy runtime configuration (read + admin write, with CIDR /
country-code / upstream validation) and Discord webhook configuration
(read / admin write / test). Token-protected; mutating routes require admin.
"""

import os
import re
import json
import logging
from urllib.parse import urlparse

import requests
from flask import Blueprint, request, jsonify

from auth import token_required, role_required
import services

logger = logging.getLogger("SecuriSphereBackend")

bp = Blueprint("config_routes", __name__)


# ============================================================
# WAF / Reverse-proxy configuration
# ============================================================

WAF_CONFIG_DIR     = os.getenv("WAF_CONFIG_DIR", "/etc/waf/conf.d")
WAF_CONFIG_FILE    = os.path.join(WAF_CONFIG_DIR, "runtime.json")
WAF_ADMIN_URL      = os.getenv("WAF_ADMIN_URL", "http://waf-proxy:8081")
WAF_PUBLIC_URL     = os.getenv("WAF_PUBLIC_URL", "http://localhost:8088")
WAF_PUBLIC_TLS_URL = os.getenv("WAF_PUBLIC_TLS_URL", "https://localhost:8443")

# Defaults applied on read; kept in sync with waf-proxy/lua/waf_config.lua
_WAF_DEFAULTS = {
    "upstream": "",
    "waf_enabled": True,
    "rate_limit_rpm": 600,
    "tls_enabled": False,
    "captcha_enabled": False,
    "geo_enabled": False,
    "ip_allowlist": [],
    "ip_blocklist": [],
    "geo_blocklist": [],
}

# Valid ISO 3166-1 alpha-2 country codes (compact superset commonly supported
# by Cloudflare / CloudFront country headers). Anything outside is rejected.
_ISO_CC_RE = re.compile(r"^[A-Z]{2}$")

# IPv4 CIDR validation — matches waf-proxy/lua/iputils.lua semantics.
_CIDR_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$")


def _validate_cidr(s: str) -> str:
    s = (s or "").strip()
    if not s:
        raise ValueError("empty CIDR")
    if not _CIDR_RE.match(s):
        raise ValueError(f"invalid CIDR: {s}")
    ip_part, _, bits_part = s.partition("/")
    octets = ip_part.split(".")
    for o in octets:
        n = int(o)
        if n < 0 or n > 255:
            raise ValueError(f"invalid octet in {s}")
    if bits_part:
        b = int(bits_part)
        if b < 0 or b > 32:
            raise ValueError(f"invalid prefix length in {s}")
    return s


def _validate_cc(s: str) -> str:
    s = (s or "").strip().upper()
    if not _ISO_CC_RE.match(s):
        raise ValueError(f"invalid country code: {s}")
    return s


def _coerce_str_list(value, validator, *, max_items=256):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected list")
    if len(value) > max_items:
        raise ValueError(f"too many items (max {max_items})")
    out = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("list items must be strings")
        out.append(validator(item))
    # de-dup preserving order
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _read_waf_config():
    cfg = dict(_WAF_DEFAULTS)
    try:
        with open(WAF_CONFIG_FILE, "r") as f:
            on_disk = json.load(f) or {}
            for k in _WAF_DEFAULTS:
                if k in on_disk:
                    cfg[k] = on_disk[k]
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("Failed to read WAF config: %s", e)
    return cfg


def _validate_upstream(url: str) -> str:
    """Return scheme://host[:port] or '' if invalid. Strips path/query."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    p = urlparse(url)
    if not p.hostname:
        raise ValueError("Missing hostname")
    # Reject localhost / internal network targets to prevent SSRF pivots.
    # For local demos, set ALLOW_LOCALHOST_UPSTREAM=1 to opt in.
    host = p.hostname.lower()
    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if host in blocked_hosts and os.getenv("ALLOW_LOCALHOST_UPSTREAM", "0") != "1":
        raise ValueError("Cannot protect localhost")
    port = f":{p.port}" if p.port else ""
    return f"{p.scheme}://{p.hostname}{port}"


@bp.route('/api/config/proxy', methods=['GET'])
@token_required
def get_proxy_config():
    cfg = _read_waf_config()
    # Live stats from waf-proxy admin endpoint
    stats = {}
    try:
        r = requests.get(f"{WAF_ADMIN_URL}/waf/stats", timeout=1.5)
        if r.ok:
            stats = r.json()
    except Exception as e:
        stats = {"error": str(e)[:120]}
    return jsonify({
        "status": "success",
        "data": {
            "config":        cfg,
            "stats":         stats,
            "public_url":    WAF_PUBLIC_URL,
            "public_tls_url":WAF_PUBLIC_TLS_URL,
        }
    })


@bp.route('/api/config/proxy', methods=['POST'])
@token_required
@role_required('admin')
def set_proxy_config():
    body = request.get_json(silent=True) or {}

    # Load existing config so callers can PATCH partial updates.
    new_cfg = _read_waf_config()

    try:
        if "upstream" in body:
            new_cfg["upstream"] = _validate_upstream(body.get("upstream") or "")
        if "waf_enabled" in body:
            new_cfg["waf_enabled"] = bool(body.get("waf_enabled"))
        if "rate_limit_rpm" in body:
            rl = int(body.get("rate_limit_rpm") or 600)
            new_cfg["rate_limit_rpm"] = max(10, min(rl, 60000))
        if "tls_enabled" in body:
            new_cfg["tls_enabled"] = bool(body.get("tls_enabled"))
        if "captcha_enabled" in body:
            new_cfg["captcha_enabled"] = bool(body.get("captcha_enabled"))
        if "geo_enabled" in body:
            new_cfg["geo_enabled"] = bool(body.get("geo_enabled"))
        if "ip_allowlist" in body:
            new_cfg["ip_allowlist"] = _coerce_str_list(body.get("ip_allowlist"), _validate_cidr)
        if "ip_blocklist" in body:
            new_cfg["ip_blocklist"] = _coerce_str_list(body.get("ip_blocklist"), _validate_cidr)
        if "geo_blocklist" in body:
            new_cfg["geo_blocklist"] = _coerce_str_list(body.get("geo_blocklist"), _validate_cc, max_items=64)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    try:
        os.makedirs(WAF_CONFIG_DIR, exist_ok=True)
        tmp = WAF_CONFIG_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(new_cfg, f, indent=2)
        os.replace(tmp, WAF_CONFIG_FILE)
    except Exception as e:
        return jsonify({"status": "error", "message": f"write failed: {e}"}), 500

    reload_err = None
    try:
        requests.get(f"{WAF_ADMIN_URL}/waf/reload", timeout=2)
    except Exception as e:
        reload_err = str(e)[:120]

    return jsonify({
        "status":         "success",
        "data":           new_cfg,
        "public_url":     WAF_PUBLIC_URL,
        "public_tls_url": WAF_PUBLIC_TLS_URL,
        "reload_err":     reload_err,
    })


# ============================================================
# DISCORD WEBHOOK CONFIGURATION ROUTES
# ============================================================

# GET Endpoint to retrieve current config
@bp.route('/api/config/discord', methods=['GET'])
@token_required
def get_discord_config():
    try:
        # Fetch from Redis key 'config:discord_webhook'
        url = services.redis_client.get('config:discord_webhook')
        return jsonify({
            "status": "success",
            "url": url if url else ""
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# POST Endpoint to save config
@bp.route('/api/config/discord', methods=['POST'])
@token_required
@role_required('admin')
def set_discord_config():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if url:
            # Strict: only allow Discord HTTPS webhook URLs (anti-SSRF + anti-data-exfil)
            if not (url.startswith("https://discord.com/api/webhooks/")
                    or url.startswith("https://discordapp.com/api/webhooks/")):
                return jsonify({"status": "error", "message": "Only Discord HTTPS webhook URLs are accepted"}), 400
            services.redis_client.set('config:discord_webhook', url)
        else:
            # If empty string provided, delete the key (disable feature)
            services.redis_client.delete('config:discord_webhook')

        return jsonify({"status": "success", "message": "Configuration saved"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# POST Endpoint to test the webhook immediately
@bp.route('/api/config/discord/test', methods=['POST'])
@token_required
@role_required('admin')
def test_discord_config():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({"status": "error", "message": "No URL provided"}), 400

        # Validate webhook URL — must be Discord HTTPS endpoint
        if not url.startswith("https://discord.com/api/webhooks/") and \
           not url.startswith("https://discordapp.com/api/webhooks/"):
            return jsonify({"status": "error", "message": "Only Discord HTTPS webhook URLs are accepted"}), 400

        payload = {
            "content": "**SecuriSphere Test:** Notification system is operational."
        }
        # Send actual request to Discord
        resp = requests.post(url, json=payload, timeout=5)

        if resp.status_code in [200, 204]:
            return jsonify({"status": "success", "message": "Test message sent!"})
        else:
            return jsonify({"status": "error", "message": f"Discord returned {resp.status_code}"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
