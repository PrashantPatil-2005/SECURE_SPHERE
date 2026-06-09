FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY bff/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bff/ /app/bff/
COPY engine/mitre/ /app/engine/mitre/
ENV PYTHONPATH=/app/engine
EXPOSE 8001
HEALTHCHECK CMD curl -fsS http://localhost:8001/health || exit 1
CMD ["uvicorn", "bff.main:app", "--host", "0.0.0.0", "--port", "8001"]
