.PHONY: help dev migrate up down test clean logs shell seed

# Default target
help:
	@echo "Mail Gateway - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev      - Start development server (local Python)"
	@echo "  make migrate  - Run database migrations"
	@echo "  make up       - Start all services with docker-compose"
	@echo "  make down     - Stop all services"
	@echo "  make test     - Run pytest suite"
	@echo "  make clean    - Clean up containers and volumes"
	@echo "  make logs     - Show application logs"
	@echo "  make shell    - Open shell in running app container"
	@echo "  make seed     - Create initial API key (run once)"
	@echo ""

# Development server (local)
dev:
	@echo "Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
migrate:
	@echo "Running database migrations..."
	alembic upgrade head

# Start services with docker-compose
up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started. App available at http://localhost:8000"
	@echo "Metrics available at http://localhost:8000/metrics"
	@echo "API docs available at http://localhost:8000/docs"

# Stop services
down:
	@echo "Stopping all services..."
	docker-compose down

# Run tests
test:
	@echo "Running test suite with coverage..."
	PYTHONPATH=. python3 -m pytest tests -v --cov=app --cov-report=term-missing --cov-fail-under=90

# Clean up everything
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Show logs
logs:
	@echo "Showing application logs..."
	docker-compose logs -f app

# Open shell in app container
shell:
	@echo "Opening shell in app container..."
	docker-compose exec app /bin/bash

# Create initial API key
seed:
	@echo "Creating initial API key..."
	python scripts/seed.py

# Development setup (install dependencies)
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Run linting
lint:
	@echo "Running code quality checks..."
	flake8 app/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	black --check app/ tests/
	mypy app/

# Format code
format:
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/

# Run security scan
security:
	@echo "Running security scan..."
	bandit -r app/ -f json -o bandit-report.json || echo "Security issues found - check bandit-report.json"

# Database reset (development only)
reset-db:
	@echo "Resetting database..."
	docker-compose down postgres
	docker volume rm mail-gateway_postgres_data || true
	docker-compose up -d postgres
	sleep 5
	make migrate
	make seed