.PHONY: setup backend frontend dev prod preview help build-package sync-cursor-commands

# Used by `make preview`: the project to serve and the port to serve it on.
PROJECT ?=
PORT ?= 8089
CONFIG ?=
WHEEL = $(lastword $(sort $(wildcard $(CURDIR)/dist/trellis_datamodel-*.whl)))

help:
	@echo "Trellis Data Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make install-uv    - Install uv package manager"
	@echo "  make setup         - Install dependencies for backend and frontend"
	@echo "  make backend      - Start backend server (API on http://localhost:8089)"
	@echo "  make frontend     - Start frontend dev server (UI on http://localhost:5173)"
	@echo "  make dev          - Start both backend and frontend (requires two terminals)"
	@echo "  make prod         - Build frontend and run production backend server"
	@echo "  make build-package - Build frontend and package for distribution"
	@echo "  make preview       - Build the wheel and serve another local project (PROJECT=path [PORT=8089])"
	@echo "  make test-smoke    - Quick smoke test (catches 500 errors, runtime crashes)"
	@echo "  make test-unit     - Run unit tests"
	@echo "  make test-e2e      - Run E2E tests (auto-starts backend with test data)"
	@echo "  make test-all      - Run all tests (check + smoke + unit + e2e)"
	@echo "  make test-check    - Run TypeScript/compilation check"
	@echo "  make sync-cursor-commands - Copy .ai_agent/commands into .cursor/commands for Cursor"
	@echo "  make help          - Show this help message"

install-uv:
	@echo "Installing uv..."
	pip install uv

setup: install-uv sync-cursor-commands
	@echo "Installing backend dependencies..."
	uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

sync-cursor-commands:
	@bash scripts/sync_cursor_commands.sh

backend:
	@echo "Starting backend server..."
	uv run trellis serve

frontend:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev

dev: 
	@echo "Starting backend and frontend development servers..."
	@echo "Backend will be available at http://localhost:8089"
	@echo "Frontend will be available at http://localhost:5173"
	@echo ""
	@echo "Note: This requires running in separate terminals or using tmux/screen."
	@echo "Run in Terminal 1: make backend"
	@echo "Run in Terminal 2: make frontend"

prod:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Starting backend server..."
	uv run trellis serve

build-package:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Copying frontend build to package..."
	rm -rf trellis_datamodel/static/*
	cp -r frontend/build/* trellis_datamodel/static/
	@echo "Building Python package..."
	uv build
	@echo "Package built! Find wheels in dist/"

# Preview the local build inside another project on this machine.
# Builds the wheel, installs it into that project's env, and serves it there.
# Usage: make preview PROJECT=../nba-data [PORT=8089] [CONFIG=trellis.yml]
preview: build-package
	@if [ -z "$(PROJECT)" ]; then \
		echo "Usage: make preview PROJECT=/path/to/project [PORT=8089]"; \
		exit 1; \
	fi
	@if [ -z "$(WHEEL)" ]; then echo "No wheel found in dist/"; exit 1; fi
	@echo "Installing $(WHEEL) into $(PROJECT)..."
	cd "$(PROJECT)" && uv pip install --reinstall "$(WHEEL)"
	@echo "Serving $(PROJECT) at http://localhost:$(PORT)"
	cd "$(PROJECT)" && uv run --no-sync trellis run -p $(PORT) $(if $(CONFIG),-c $(CONFIG))

publish:
	@echo "Publishing package to PyPI..."
	uv publish --token ${PYPI_TOKEN}

test-smoke:
	@echo "Running smoke test (catches 500 errors, runtime crashes)..."
	cd frontend && npm run test:smoke

test-unit:
	@echo "Running unit tests..."
	cd frontend && npm run test:unit

test-e2e:
	@echo "Running E2E tests..."
	@echo "Playwright will automatically start backend with test data and frontend."
	cd frontend && npm run test:e2e

test-all:
	@echo "Running all tests (check + smoke + unit + e2e)..."
	cd frontend && npm run test

test-check:
	@echo "Running TypeScript/compilation check..."
	cd frontend && npm run check

create_mock_dbt_project:
	@echo "Creating mock project..."
	uv pip install ".[dbt-example]" && uv run trellis generate-company-data

dbt_refresh:
	@echo "Refreshing dbt artifacts ..."
	cd dbt_company_dummy_entity && uv run dbt run && uv run dbt docs generate