FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ingestion/ /app/ingestion/
COPY engine/shared/ /app/engine/shared/
ENV PYTHONPATH=/app/engine
WORKDIR /app
EXPOSE 5010
HEALTHCHECK CMD curl -fsS http://localhost:5010/health || exit 1
CMD ["uvicorn", "ingestion.main:app", "--host", "0.0.0.0", "--port", "5010"]
