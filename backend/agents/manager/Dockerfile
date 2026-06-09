FROM python:3.11-slim
WORKDIR /app
COPY manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt requests
COPY manager/ /app/manager/
EXPOSE 8514
CMD ["uvicorn", "manager.main:app", "--host", "0.0.0.0", "--port", "8514"]
