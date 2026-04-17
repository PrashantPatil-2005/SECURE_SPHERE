FROM python:3.10-slim
RUN apt-get update && apt-get install -y curl iputils-ping net-tools nmap && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Default: run the legacy orchestrator. Override CMD to run run_all.py:
#   docker-compose run --rm attack-simulator python run_all.py --scenario a
CMD ["python", "-u", "attack_orchestrator.py"]
