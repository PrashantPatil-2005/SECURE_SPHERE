# Docker Host Agent Dockerfile
# Multi-stage build with Trivy installation

FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for Trivy
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    lsb-release \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install Trivy
RUN wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" > /etc/apt/sources.list.d/trivy.list \
    && apt-get update && apt-get install -y trivy \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash agent

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy Trivy from builder
COPY --from=builder /usr/bin/trivy /usr/bin/trivy
COPY --from=builder /usr/share/keyrings/trivy.gpg /usr/share/keyrings/trivy.gpg

# Install Python dependencies
COPY backend/agents/docker_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY backend/agents/docker_agent/agent.py .

# Create non-root user
RUN useradd -m -s /bin/bash agent && chown -R agent:agent /app

USER agent

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8515/health || exit 1

# Run agent
CMD ["python", "-u", "agent.py"]

EXPOSE 8515
