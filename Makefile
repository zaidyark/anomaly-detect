# Graph-Based Network Anomaly Detection — developer tasks (Linux / macOS)
# Windows users: use make.bat with the same target names.

PYTHON ?= python3
VENV   := .venv
PIP    := $(VENV)/bin/pip
PY     := $(VENV)/bin/python

.PHONY: help venv install run test test-verbose convert-ctu13 convert-iot23 docker docker-down clean

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

venv: ## Create the virtual environment
	$(PYTHON) -m venv $(VENV)

install: venv ## Create the venv and install dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: ## Start the dashboard at http://127.0.0.1:8050
	$(PY) app.py

test: ## Run the test suite
	$(PY) -m pytest tests/ -q

test-verbose: ## Run the test suite with full output
	$(PY) -m pytest tests/ -v

convert-ctu13: ## Convert a CTU-13 capture: make convert-ctu13 CAPTURE=path/to/file.binetflow
ifndef CAPTURE
	$(error Usage: make convert-ctu13 CAPTURE=path/to/capture.binetflow [OUT=data/name.csv] [NAME="Scenario name"])
endif
	$(PY) scripts/convert_ctu13.py $(CAPTURE) $(or $(OUT),data/ctu13_scenario9.csv) "$(or $(NAME),CTU-13 Real Botnet (Neris))"

convert-iot23: ## Convert an IoT-23 conn.log.labeled: make convert-iot23 CAPTURE=path/to/conn.log.labeled
ifndef CAPTURE
	$(error Usage: make convert-iot23 CAPTURE=path/to/conn.log.labeled [OUT=data/name.csv] [NAME="Scenario name"])
endif
	$(PY) scripts/convert_iot23.py $(CAPTURE) $(or $(OUT),data/iot23_scenario3.csv) "$(or $(NAME),IoT-23 Real Botnet (Port Scan))"

docker: ## Build and run with Docker Compose
	docker compose up --build

docker-down: ## Stop the Docker Compose stack
	docker compose down

clean: ## Remove the venv, caches, and build artifacts
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -not -path "./$(VENV)/*" -exec rm -rf {} +
