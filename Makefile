setup:
	./scripts/setup.sh

start:
	docker-compose up -d

stop:
	docker-compose down

restart: stop start

reset: ## DANGER: Stop all containers and permanently delete all data volumes
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║  WARNING: This will permanently delete all data.    ║"
	@echo "║  PostgreSQL, Elasticsearch, and Redis data lost.    ║"
	@echo "╚══════════════════════════════════════════════════════╝"
	@echo ""
	@read -p "Type 'yes' to confirm reset: " _confirm && [ "$$_confirm" = "yes" ] || (echo "Reset aborted." && exit 1)
	docker-compose down -v
	@echo "Volumes deleted. Re-initialising..."
	$(MAKE) setup
	@echo ""
	@echo "Reset complete. Run 'make start' to restart SecuriSphere."

health:
	./scripts/health_check.sh

logs:
	docker-compose logs -f

logs-redis:
	docker-compose logs -f redis

logs-db:
	docker-compose logs -f database

ps:
	docker-compose ps

shell-redis:
	docker exec -it securisphere-redis redis-cli

shell-db:
	docker exec -it securisphere-db psql -U securisphere_user -d securisphere_db

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf logs/*.log

help:
	@echo "Available commands:"
	@echo "  setup       - Run initial setup script"
	@echo "  start       - Start services with docker-compose"
	@echo "  stop        - Stop services"
	@echo "  restart     - Restart services"
	@echo "  reset       - Reset environment (remove containers and volumes)"
	@echo "  health      - Run health check script"
	@echo "  logs        - View all logs"
	@echo "  logs-redis  - View redis logs"
	@echo "  logs-db     - View database logs"
	@echo "  ps          - List running containers"
	@echo "  shell-redis - open redis-cli"
	@echo "  shell-db    - open psql shell"
	@echo "  clean       - Remove temporary files"

build:
	docker-compose build

build-api:
	docker-compose build api-server

build-auth:
	docker-compose build auth-service

test-api:
	@echo "--- Health Check ---"
	@curl -s http://localhost:5000/api/health | python -m json.tool
	@echo "--- List Products ---"
	@curl -s http://localhost:5000/api/products | python -m json.tool
	@echo "--- Search Products ---"
	@curl -s "http://localhost:5000/api/products/search?q=laptop" | python -m json.tool
	@echo "--- SQL Injection Test ---"
	@curl -s "http://localhost:5000/api/products/search?q=' OR '1'='1" | python -m json.tool
	@echo "--- Path Traversal Test ---"
	@curl -s "http://localhost:5000/api/files?name=../../../etc/passwd" | python -m json.tool
	@echo "--- Admin Config ---"
	@curl -s http://localhost:5000/api/admin/config | python -m json.tool

test-auth:
	@echo "--- Auth Status ---"
	@curl -s http://localhost:5001/auth/status | python -m json.tool
	@echo "--- Successful Login ---"
	@curl -s -X POST http://localhost:5001/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python -m json.tool
	@echo "--- Failed Login ---"
	@curl -s -X POST http://localhost:5001/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"wrongpass"}' | python -m json.tool
	@echo "--- Reset All ---"
	@curl -s -X POST http://localhost:5001/auth/reset-all | python -m json.tool

test-phase2:
	python -m pytest tests/test_phase2.py -v

shell-api:
	docker exec -it securisphere-api /bin/bash

shell-auth:
	docker exec -it securisphere-auth /bin/bash

logs-api:
	docker-compose logs -f api-server

logs-auth:
	docker-compose logs -f auth-service

# Phase 3 Targets
build-monitors:
	docker-compose build network-monitor api-monitor auth-monitor

start-monitors:
	docker-compose up -d network-monitor api-monitor auth-monitor

stop-monitors:
	docker-compose stop network-monitor api-monitor auth-monitor

test-monitors:
	bash scripts/test_monitors.sh

test-phase3:
	python -m pytest tests/test_phase3.py -v

logs-netmon:
	docker-compose logs -f network-monitor

logs-apimon:
	docker-compose logs -f api-monitor

logs-authmon:
	docker-compose logs -f auth-monitor

monitor-events:
	docker exec -it securisphere-redis redis-cli SUBSCRIBE security_events

# Phase 4 Targets
build-backend:
	docker-compose build backend

start-backend:
	docker-compose up -d backend

stop-backend:
	docker-compose stop backend

logs-backend:
	docker-compose logs -f backend

test-backend:
	bash scripts/test_backend.sh

test-phase4:
	python -m pytest tests/test_phase4.py -v

shell-backend:
	docker exec -it securisphere-backend /bin/bash

# Phase 5 Targets
build-frontend:
	docker-compose build dashboard

start-frontend:
	docker-compose up -d dashboard

stop-frontend:
	docker-compose stop dashboard

logs-frontend:
	docker-compose logs -f dashboard

open-dashboard:
	echo "Opening http://localhost:3000" && (xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || start http://localhost:3000 2>/dev/null)

# Phase 6 Targets
build-engine:
	docker-compose build correlation-engine

start-engine:
	docker-compose up -d correlation-engine

stop-engine:
	docker-compose stop correlation-engine

logs-engine:
	docker-compose logs -f correlation-engine

test-correlation:
	bash scripts/test_correlation.sh

engine-stats:
	curl -s http://localhost:5070/engine/stats | python3 -m json.tool || echo "Failed to fetch stats"

# Phase 7: Attack Simulator (named scenarios)
build-simulator:
	docker-compose build attack-simulator

# Original scenarios (kept for backwards compatibility)
attack-killchain:
	docker-compose run --rm attack-simulator full_kill_chain

attack-api:
	docker-compose run --rm attack-simulator api_abuse

attack-creds:
	docker-compose run --rm attack-simulator credential_attack

attack-benign:
	docker-compose run --rm attack-simulator benign

attack-stealth:
	docker-compose run --rm attack-simulator stealth

attack-all:
	docker-compose run --rm attack-simulator all

# New named scenarios A / B / C (docker attack-simulator variants)
# NOTE: attack-simulator is under the 'attack' profile — must pass --profile attack
attack-a: ## Scenario A: Brute Force → Credential Compromise → Data Exfiltration
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario a

attack-b: ## Scenario B: Recon → SQL Injection → Privilege Escalation
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario b

attack-c: ## Scenario C: Multi-Hop Lateral Movement across 3+ services
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario c

attack-abc: ## Run all three named scenarios in sequence
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario all

# Host-run attacker scenarios (attacker/ package, talk to localhost endpoints).
# Layer background noise with NOISE=1: `make attacker-a NOISE=1 SPEED=fast`
SPEED ?= normal
NOISE ?=
NOISE_FLAG := $(if $(NOISE),--noise,)

attacker-a: ## Host-run Scenario A (brute force → cred compromise → exfil, 4 stages)
	python -m attacker.scenario_a --speed $(SPEED) $(NOISE_FLAG)

attacker-b: ## Host-run Scenario B (recon → SQLi → priv esc, 3 stages)
	python -m attacker.scenario_b --speed $(SPEED) $(NOISE_FLAG)

attacker-c: ## Host-run Scenario C (multi-hop lateral movement, 4 services)
	python -m attacker.scenario_c --speed $(SPEED) $(NOISE_FLAG)

attacker-abc: attacker-a attacker-b attacker-c ## Run all three host scenarios in sequence

attacker-noise: ## Standalone background-noise generator (DURATION=60 RATE=2)
	python -m attacker.traffic_generator --duration $(or $(DURATION),60) --rate $(or $(RATE),2)

test-scenarios: ## Run scenario regression tests (mocked — no backend needed)
	python -m pytest tests/test_scenarios.py -v

attack-demo: ## Run full kill chain at demo speed for live presentations
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario all --speed demo

attack-fast: ## Run all attack scenarios at maximum speed (for CI and quick testing)
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario all --speed fast

attack-slow: ## Run all scenarios slowly for classroom or walkthrough presentations
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario all --speed slow

# Phase 16: Host-based reproducibility trial runner (3× each scenario)
# Requires: services running locally (run.bat start / docker compose up -d)
trial-a: ## Run Scenario A 3 times, record incidents + MTTD per run
	python scripts/run_attack_trials.py --scenario a

trial-b: ## Run Scenario B 3 times, record incidents + MTTD per run
	python scripts/run_attack_trials.py --scenario b

trial-c: ## Run Scenario C 3 times, record incidents + MTTD per run
	python scripts/run_attack_trials.py --scenario c

trial-all: ## Run all three scenarios A/B/C 3× each
	python scripts/run_attack_trials.py --scenario all

trial-benign: ## Run benign traffic 3× to verify 0 false positives
	python scripts/run_attack_trials.py --scenario benign

# Topology Collector
build-topology:
	docker-compose build topology-collector

start-topology:
	docker-compose up -d topology-collector

logs-topology:
	docker-compose logs -f topology-collector

topology-graph: ## Fetch and display live topology graph JSON
	curl -s http://localhost:5080/topology/graph | python3 -m json.tool || echo "Topology collector not running"

# MTTD export
mttd-report: ## Print MTTD comparison table and save CSV
	python scripts/mttd_export.py

mttd-json: ## Export MTTD data as JSON only
	python scripts/mttd_export.py --format json

mttd-markdown: ## Export MTTD results as a Markdown table for the research paper
	python scripts/mttd_export.py --format markdown

# MITRE mapping
mitre-mapping: ## Fetch MITRE ATT&CK coverage from backend
	curl -s http://localhost:8000/api/mitre-mapping | python3 -m json.tool

# Kill chain drill-down (usage: make kill-chain ID=<incident_id>)
kill-chain:
	curl -s http://localhost:8000/api/kill-chains/$(ID) | python3 -m json.tool

demo:
	docker-compose run --rm attack-simulator full_kill_chain --delay demo

# One-command full demo (interactive)
demo-full: ## One-command demo: start stack, wait for health, open browser, run attack
	@bash scripts/run_demo.sh

run-demo:
	bash scripts/run_demo.sh

# Phase 8: Evaluation
evaluate:                    ## Original 5-scenario evaluation
	python backend/evaluation/run_evaluation.py --mode full

evaluate-named:              ## Named A/B/C scenario evaluation with accurate MTTD
	python backend/evaluation/run_evaluation.py --mode named

evaluate-named-full: ## Run named A/B/C scenarios, tag kill chains, measure MTTD, export markdown table
	@echo "Running SecuriSphere Named Scenario Evaluation..."
	python backend/evaluation/run_evaluation.py --mode named
	@echo ""
	@echo "Exporting MTTD results..."
	python scripts/mttd_export.py --format markdown
	@echo ""
	@echo "Saving CSV..."
	python scripts/mttd_export.py --format csv
	@echo "Done. Check mttd_results.csv for raw data."

test-integration:
	python -m pytest tests/test_integration.py -v

run-evaluation:
	bash scripts/run_evaluation.sh

health-full: ## Check health of all SecuriSphere services including topology and engine
	@echo "Checking SecuriSphere service health..."
	@curl -sf http://localhost:8000/api/metrics > /dev/null 2>&1 && echo "  ✓ Backend API        (port 8000)" || echo "  ✗ Backend API        (port 8000) — FAILED"
	@curl -sf http://localhost:5070/engine/stats > /dev/null 2>&1 && echo "  ✓ Correlation Engine (port 5070)" || echo "  ✗ Correlation Engine (port 5070) — FAILED"
	@curl -sf http://localhost:5080/topology/graph > /dev/null 2>&1 && echo "  ✓ Topology Collector (port 5080)" || echo "  ✗ Topology Collector (port 5080) — FAILED"
	@curl -sf http://localhost:3000 > /dev/null 2>&1 && echo "  ✓ React Dashboard    (port 3000)" || echo "  ✗ React Dashboard    (port 3000) — FAILED"
	@echo "Done."

test-smoke: ## Run end-to-end smoke test (requires full stack running)
	python -m pytest tests/test_smoke.py -v -s

# Phase 4: AI Narration
test-narrator: ## Unit-test the Groq narrator (no network calls)
	python -m pytest tests/test_narrator.py -v

# Phase 5: Full evaluation pipeline
evaluate-full: ## Run complete evaluation: named scenarios + MTTD export + markdown report
	@echo "Running SecuriSphere full evaluation pipeline..."
	python backend/evaluation/run_evaluation.py --mode named
	@echo ""
	python scripts/mttd_export.py --format markdown
	@echo ""
	python scripts/mttd_export.py --format csv
	@echo ""
	@echo "Evaluation complete."
	@echo "  Markdown table: run 'make mttd-markdown' to regenerate"
	@echo "  CSV data:       mttd_results.csv"

# Phase 5: CI / quick validation
ci: ## Smoke test + fast attack + verify incidents were detected (CI pipeline)
	@echo "Running SecuriSphere CI validation..."
	python -m pytest tests/test_smoke.py tests/test_narrator.py -v
	docker compose --profile attack run --rm attack-simulator python run_all.py --scenario a --speed fast
	@sleep 15
	@curl -sf http://localhost:8000/api/incidents | python3 -c \
		"import sys,json; d=json.load(sys.stdin); \
		 incs=d.get('data',{}).get('incidents',d.get('data',[])); \
		 n=len(incs) if isinstance(incs,list) else 0; \
		 print(f'CI check: {n} incidents detected'); \
		 sys.exit(0 if n>0 else 1)"
	@echo "CI validation passed ✓"

# Phase 5: Verification script
verify-phase5: ## Verify Phase 5 (Demo & Polish) implementation is complete
	@bash scripts/verify_phase5.sh

# ─── Browser Monitor (Phase 1 → wired in Phase 3) ───────────────────────────

build-browser-monitor: ## Build the browser-monitor image
	docker-compose build browser-monitor

logs-browser: ## Tail browser-monitor logs
	docker-compose logs -f browser-monitor

shell-browser: ## Shell into the browser-monitor container
	docker exec -it securisphere-browsermon /bin/bash

health-browser: ## Curl the browser-monitor /health endpoint
	@curl -sf http://localhost:5090/health && echo "" || echo "browser-monitor unhealthy"

register-demo-site: ## Register the ShopSphere web-app with the browser-monitor (demo helper)
	@curl -s -X POST http://localhost:5090/api/register-site \
		-H "Content-Type: application/json" \
		-d '{"name":"ShopSphere","url":"http://localhost:8080","email":"demo@securisphere.local"}' | \
		python3 -m json.tool || echo "registration failed"
