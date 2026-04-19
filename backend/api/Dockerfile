FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY backend/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /var/log/securisphere

# Copy API application files
COPY backend/api/ /app/

# Copy the MITRE map module shared with the correlation engine
COPY backend/engine/mitre/ /app/mitre/

# Copy the attacker module so /api/attack/run can spawn scenarios
COPY attacker/ /app/attacker/

# Expose port
EXPOSE 8000

# Create upload and sample directories
RUN mkdir -p /app/uploads/pcap /app/samples/pcap

# Run gunicornheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-u", "app.py"]
