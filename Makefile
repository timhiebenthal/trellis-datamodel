.PHONY: setup backend frontend dev prod help

help:
	@echo "dbt Data Model UI Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make install-uv  - Install uv package manager"
	@echo "  make setup       - Install dependencies for backend and frontend"
	@echo "  make backend     - Start backend server (API on http://localhost:8000)"
	@echo "  make frontend    - Start frontend dev server (UI on http://localhost:5173)"
	@echo "  make dev         - Start both backend and frontend (requires two terminals)"
	@echo "  make prod        - Build frontend and run production backend server"
	@echo "  make help        - Show this help message"

install-uv:
	@echo "Installing uv..."
	pip install uv

setup: install-uv
	@echo "Installing backend dependencies..."
	python -m uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

backend:
	@echo "Starting backend server..."
	python -m uv run python backend/main.py

frontend:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev

dev: 
	@echo "Starting backend and frontend development servers..."
	@echo "Backend will be available at http://localhost:8000"
	@echo "Frontend will be available at http://localhost:5173"
	@echo ""
	@echo "Note: This requires running in separate terminals or using tmux/screen."
	@echo "Run in Terminal 1: make backend"
	@echo "Run in Terminal 2: make frontend"

prod:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Starting backend server..."
	python -m uv run python backend/main.py


unit-test:
	@echo "Running unit tests..."
	cd frontend && npm run test:unit

e2e-test:
	@echo "Running E2E tests..."
	cd frontend && npm run test:e2e

all-test:
	@echo "Running all tests..."
	cd frontend && npm run test