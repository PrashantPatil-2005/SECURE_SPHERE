FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime deps + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin --uid 10001 app

COPY backend/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/api/ /app/
COPY backend/engine/mitre/ /app/mitre/
COPY attacker/ /app/attacker/
COPY scripts/init_db.sql /app/scripts/init_db.sql

RUN mkdir -p /var/log/securisphere /app/uploads/pcap /app/samples/pcap \
    && chown -R app:app /app /var/log/securisphere

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

# Default to gunicorn with gevent-websocket worker.
# Override via $GUNICORN_CMD for dev (e.g. plain python app.py).
ENV GUNICORN_BOOT=1 \
    GUNICORN_WORKERS=1 \
    GUNICORN_TIMEOUT=120

CMD ["sh", "-c", "exec gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w ${GUNICORN_WORKERS:-1} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile - -b 0.0.0.0:8000 app:app"]
