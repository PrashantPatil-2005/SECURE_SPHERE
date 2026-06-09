FROM python:3.11-slim
WORKDIR /app
COPY search/indexer.py /app/indexer.py
RUN pip install --no-cache-dir redis>=5.0.0
CMD ["python", "-u", "indexer.py"]
