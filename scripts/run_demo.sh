#!/usr/bin/env bash
# run_demo.sh — One-command automated demo launcher for SecuriSphere
# Usage: bash scripts/run_demo.sh
# Or via Makefile: make demo-full

set -euo pipefail

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         SecuriSphere — Live Demo                 ║"
echo "║  Topology-Aware Kill Chain Detection System      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# --- STEP 1: Start the stack ---
echo "Starting SecuriSphere stack..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start the stack."
    exit 1
fi

# --- STEP 2: Poll health endpoints ---
echo "Waiting for all services to become healthy..."
MAX_WAIT=90
POLL_INTERVAL=4
elapsed=0
all_healthy=0

while [ $elapsed -lt $MAX_WAIT ]; do
    h1=$(curl -sf http://localhost:8000/api/metrics  > /dev/null 2>&1 && echo 1 || echo 0)
    h2=$(curl -sf http://localhost:5070/engine/stats  > /dev/null 2>&1 && echo 1 || echo 0)
    h3=$(curl -sf http://localhost:5080/topology/graph > /dev/null 2>&1 && echo 1 || echo 0)
    h4=$(curl -sf http://localhost:3000               > /dev/null 2>&1 && echo 1 || echo 0)

    if [ "$h1" = "1" ] && [ "$h2" = "1" ] && [ "$h3" = "1" ] && [ "$h4" = "1" ]; then
        all_healthy=1
        break
    fi

    printf "."
    sleep $POLL_INTERVAL
    elapsed=$((elapsed + POLL_INTERVAL))
done

if [ $all_healthy -ne 1 ]; then
    echo ""
    echo "ERROR: Services did not become healthy within ${MAX_WAIT}s"
    echo "Run 'make health-full' to see which service failed."
    exit 1
fi

echo ""
echo "All services healthy ✓"

# --- STEP 3: Open browser ---
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:3000 &
elif command -v open > /dev/null 2>&1; then
    open http://localhost:3000
else
    start http://localhost:3000 2>/dev/null || true
fi
echo "Dashboard opened at http://localhost:3000"

# --- STEP 4: Set demo flag in Redis ---
docker exec securisphere-redis redis-cli set demo:active 1 ex 300 > /dev/null 2>&1 || true
docker exec securisphere-redis redis-cli set demo:scenario "Scenario A — Brute Force to Exfiltration" ex 300 > /dev/null 2>&1 || true

# --- STEP 5: Countdown ---
for i in 5 4 3 2 1; do
    printf "\rLaunching attack in %s seconds..." "$i"
    sleep 1
done
printf "\r%-50s\n" "Launching attack now..."

# --- STEP 6: Run the attack ---
docker-compose run --rm attack-simulator python run_all.py --scenario a --speed demo

# --- STEP 7: Clear demo flag and print summary ---
docker exec securisphere-redis redis-cli del demo:active demo:scenario > /dev/null 2>&1 || true

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Demo complete."
echo "  Dashboard:        http://localhost:3000"
echo "  Kill chains:      visible in the Incidents tab"
echo "  MTTD data:        run 'make evaluate-named-full'"
echo "  Research table:   run 'make mttd-markdown'"
echo "═══════════════════════════════════════════════════"
