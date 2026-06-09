# Security Considerations

## Authentication
- JWT HS256 with `JWT_SECRET` ≥16 chars (required in production)
- Account lockout after 5 failed attempts
- Token blocklist on logout

## SSRF protection
- `ALLOW_LOCALHOST_UPSTREAM=0` by default; forbidden when `FLASK_ENV=production`
- Engine proxy validates upstream URLs

## Secrets
- All credentials via environment variables
- `.env` gitignored; use `.env.example` for templates

## Container hardening
- Non-root users in production Dockerfiles (`app` uid 10001)
- Read-only root filesystem where feasible
- Docker socket access limited to topology-collector and agent-manager

## Alert channels
- Discord webhooks stored in Redis `config:discord_webhook` (admin-only write)
- SMTP credentials via `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`

## Rate limiting
- Flask-Limiter on auth endpoints (Redis-backed)
