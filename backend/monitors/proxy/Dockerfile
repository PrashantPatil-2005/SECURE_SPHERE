FROM python:3.10-slim

WORKDIR /app

COPY proxy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY proxy/ /app/

CMD ["python", "-u", "proxy_monitor.py"]
