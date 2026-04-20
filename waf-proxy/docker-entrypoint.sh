#!/usr/bin/env bash
set -e

# Ensure runtime config exists (first boot)
mkdir -p /etc/waf/conf.d
if [ ! -f /etc/waf/conf.d/runtime.json ]; then
    cat > /etc/waf/conf.d/runtime.json <<'EOF'
{
  "upstream": "",
  "waf_enabled": true,
  "rate_limit_rpm": 600,
  "tls_enabled": false,
  "captcha_enabled": false,
  "geo_enabled": false,
  "ip_allowlist": [],
  "ip_blocklist": [],
  "geo_blocklist": []
}
EOF
fi

# Generate self-signed cert if missing (used by optional TLS listener on 8443)
mkdir -p /etc/waf/ssl
if [ ! -f /etc/waf/ssl/cert.pem ] || [ ! -f /etc/waf/ssl/key.pem ]; then
    echo "[entrypoint] generating self-signed cert at /etc/waf/ssl/*"
    openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
        -subj "/CN=securisphere-waf" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
        -keyout /etc/waf/ssl/key.pem \
        -out    /etc/waf/ssl/cert.pem 2>/dev/null
    chmod 600 /etc/waf/ssl/key.pem
fi

exec "$@"
