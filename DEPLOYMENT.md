# SecuriSphere — Production Deployment Guide

This document covers hardened production deployment via Docker Compose,
Render.com, and a generic VM/Kubernetes target.

---

## 1. Pre-flight checklist

**Before any deploy:**

- [ ] Rotate the leaked `HF_API_TOKEN` at https://huggingface.co/settings/tokens
- [ ] Generate a fresh `JWT_SECRET`: `openssl rand -hex 32`
- [ ] Generate a strong DB password (≥ 24 chars random)
- [ ] Set `CORS_ORIGINS` to your real frontend origin(s), never `*`
- [ ] Decide where you store secrets:
      - Docker Compose: `.env` file readable only by deploy user (`chmod 600`)
      - Render: dashboard env vars (the ones marked `sync: false`)
      - Kubernetes: `Secret` resources (never `ConfigMap`)
- [ ] Set `FLASK_ENV=production`
- [ ] Set `ALLOW_LOCALHOST_UPSTREAM=0`
- [ ] Set `ALLOW_PLAINTEXT_LOGIN=0` (or unset)
- [ ] Confirm DB and Redis are NOT exposed to the public internet

---

## 2. Required env vars

| Var | Required? | Notes |
|---|---|---|
| `JWT_SECRET` | yes | ≥ 16 bytes; backend refuses to boot otherwise |
| `POSTGRES_PASSWORD` or `DATABASE_URL` | yes | one of the two |
| `POSTGRES_HOST/PORT/DB/USER` | yes if no `DATABASE_URL` | |
| `REDIS_HOST/PORT` | yes | |
| `CORS_ORIGINS` | yes | comma-separated origins; wildcard rejected in prod |
| `FLASK_ENV` | recommended | set to `production` |
| `ADMIN_BOOTSTRAP_USER` + `ADMIN_BOOTSTRAP_PASSWORD` | first deploy | seeds the first admin via the auth blueprint |
| `JWT_EXPIRATION_HOURS` | optional | default 1 |
| `RATE_LIMIT_DEFAULT/LOGIN/ATTACK` | optional | Flask-Limiter format |
| `HF_API_TOKEN` | optional | enables AI kill-chain narration |
| `GUNICORN_WORKERS` | optional | default 1 (gevent-websocket needs 1 unless you front with sticky LB) |
| `ALLOW_LOCALHOST_UPSTREAM` | must be `0` | refuses prod boot if `1` |

---

## 3. Docker Compose (single VM)

```bash
# 1. Provision the host
sudo apt-get install -y docker.io docker-compose-plugin

# 2. Clone and configure
git clone <repo> /opt/securisphere && cd /opt/securisphere
cp .env.example .env
chmod 600 .env
$EDITOR .env   # fill all CHANGE_ME values

# 3. Build + start
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Verify
curl -fsS http://localhost:8000/api/health
docker compose ps

# 5. Bootstrap admin (one-time; if not using ADMIN_BOOTSTRAP_* env vars)
docker compose exec backend python /app/scripts/bootstrap_admin.py \
    --username admin --email admin@yourorg.example
```

### TLS termination

Production runs behind a TLS proxy you control:

- **Caddy** (simplest): `caddy reverse-proxy --from securisphere.example.com --to :3000`
- **nginx + certbot**: standard Let's Encrypt setup, proxy to `localhost:3000` (frontend) and `localhost:8000` (backend) — or front only the frontend container, which already proxies `/api` and `/socket.io` to the backend over the docker network.
- **Cloudflare Tunnel**: zero-trust + free TLS.

Set `CORS_ORIGINS` to the public HTTPS origin (e.g. `https://securisphere.example.com`).

### Backups

```bash
# Postgres dump (daily cron)
docker compose exec -T database pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > /var/backups/securisphere-$(date +%F).sql.gz
```

Redis is a cache; not strictly required to back up. If you do:
`docker compose exec redis redis-cli SAVE` then copy `redis-data` volume.

---

## 4. Render.com

`render.yaml` is pre-configured for gunicorn + gevent-websocket worker.

1. Push the repo.
2. Render → "Blueprints" → New → point at the repo. It picks up `render.yaml`.
3. After the first build, set the dashboard env vars marked `sync: false`:
   - `CORS_ORIGINS` — your `securisphere-dashboard` Render URL
   - `ADMIN_BOOTSTRAP_USER` / `ADMIN_BOOTSTRAP_PASSWORD` / `ADMIN_BOOTSTRAP_EMAIL`
   - `HF_API_TOKEN`
   - For frontend: `VITE_API_URL` = backend's `*.onrender.com` URL
4. Trigger a redeploy. The backend will create the admin on next boot.
5. Render's free tier sleeps; for actual production use the `starter` plan or higher.

Render-specific gotchas:

- Render free Redis has no persistence; treat all Redis state as volatile.
- Bind to `$PORT`, not a fixed port (already configured in `render.yaml`).
- WebSockets work on `starter` plans and up.

---

## 5. Kubernetes (generic)

Convert each compose service to a Deployment + Service:

```yaml
# Example: backend
apiVersion: apps/v1
kind: Deployment
metadata: { name: securisphere-backend }
spec:
  replicas: 1   # increase only with sticky sessions for /socket.io
  selector: { matchLabels: { app: securisphere-backend } }
  template:
    metadata: { labels: { app: securisphere-backend } }
    spec:
      containers:
        - name: backend
          image: registry.example.com/securisphere-backend:1.0.0
          ports: [{ containerPort: 8000 }]
          envFrom:
            - secretRef: { name: securisphere-secrets }
            - configMapRef: { name: securisphere-config }
          readinessProbe:
            httpGet: { path: /api/health, port: 8000 }
          livenessProbe:
            httpGet: { path: /api/health, port: 8000 }
          resources:
            limits: { memory: 1Gi, cpu: "1" }
            requests: { memory: 512Mi, cpu: "200m" }
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: false
            capabilities: { drop: [ALL] }
```

Use a managed Postgres (RDS / Cloud SQL / Neon) and managed Redis (Upstash / ElastiCache). Pass the connection string as `DATABASE_URL` in the Secret.

Front the frontend Service with an Ingress + cert-manager.

---

## 6. Observability

Already wired:
- `/api/health` — process + Redis liveness
- `/api/system/status` — per-monitor freshness, correlation engine ping
- Container `HEALTHCHECK` directives on all services
- JSON logs to stdout (10 MB rotated x3 per service)

Recommended additions:
- **Metrics** — add `prometheus-flask-exporter` and scrape `/metrics`.
- **Alerts** — Discord webhook (`/api/config/discord`) is already supported. Tie it to incident severity ≥ high.
- **Errors** — wire Sentry by adding `sentry-sdk[flask]` and an `init()` call.
- **Uptime** — UptimeRobot / Better Stack pinging `/api/health` every minute.

---

## 7. Security hardening summary (already applied)

- JWT secret required at boot in production
- CORS wildcard rejected in production
- DB/Redis ports not exposed to host by default
- Plaintext password login gated behind `ALLOW_PLAINTEXT_LOGIN=1`
- Account lockout after 5 failed logins (15 min)
- Rate limiting on login (10/min), attack run (5/hour), default (200/min)
- Admin-only gates on: `/api/events/clear`, `/api/attack/run`, `/api/config/proxy` (POST), `/api/config/discord` (POST + test)
- Authenticated gate on `/api/incidents/<id>/status` (PATCH)
- Discord webhook URL strictly validated (only `discord.com/api/webhooks/`)
- Security response headers: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security` (prod only)
- nginx serves `Content-Security-Policy`, `Cache-Control` for hashed assets
- Backend runs as non-root user (uid 10001) in container
- gunicorn replaces Flask dev server in production

---

## 8. Operational runbook

### Rotate JWT secret
```bash
# Pick new value
NEW=$(openssl rand -hex 32)
# Update secret store (compose .env, Render dashboard, k8s Secret), redeploy.
# All existing tokens become invalid; users must re-login.
```

### Add/reset an admin
```bash
docker compose exec backend python /app/scripts/bootstrap_admin.py \
    --username someone --email someone@yourorg.example
# Prompts for password. Re-running with the same username resets the password.
```

### Wipe events / clear demo state
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"…"}' | jq -r .token)
curl -X POST http://localhost:8000/api/events/clear \
  -H "Authorization: Bearer $TOKEN"
```

### Investigate a stuck container
```bash
docker compose logs --tail=200 -f backend
docker compose exec backend python -c "from app import redis_available; print(redis_available)"
```

### Roll back
```bash
docker compose pull        # if using a registry
docker compose up -d --no-deps backend  # roll one service
# Or: docker compose down && git checkout <previous-tag> && docker compose up -d --build
```

---

## 9. Known limitations / future work

- Single backend replica (gevent-websocket is not horizontally safe without sticky sessions on `/socket.io`). Use a Redis-backed message queue for SocketIO if scaling out.
- No CSRF token on state-changing endpoints (rely on JWT bearer + CORS allowlist).
- No password complexity enforcement on user signup beyond auth blueprint defaults.
- No 2FA. Add TOTP via `pyotp` if compliance requires it.
- Audit log table not yet implemented; Discord webhook is the current alert sink.

---

## 10. First-deploy walkthrough (compose)

```bash
# 1. clone + env
git clone <repo> /opt/securisphere && cd /opt/securisphere
cp .env.example .env
sed -i "s/CHANGE_ME_strong_password/$(openssl rand -hex 16)/" .env
sed -i "s/CHANGE_ME_min_32_byte_random_string/$(openssl rand -hex 32)/" .env
$EDITOR .env   # set CORS_ORIGINS, ADMIN_BOOTSTRAP_*, FLASK_ENV=production
chmod 600 .env

# 2. boot
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. wait + verify
sleep 30
curl -fsS http://localhost:8000/api/health
curl -fsS http://localhost:3000/healthz

# 4. confirm admin works
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_BOOTSTRAP_USER\",\"password\":\"$ADMIN_BOOTSTRAP_PASSWORD\"}"

# 5. front with TLS proxy of choice (Caddy / nginx / Cloudflare Tunnel)
```

Production-ready.
