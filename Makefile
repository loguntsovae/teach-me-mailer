.PHONY: lint format clean logs shell seed reset-db check-env coverage build
.PHONY: deploy-prod deploy-staging docker-build docker-push security
.PHONY: docs-serve docs-build pre-commit-install db-shell db-backup db-restore

# Colors for output
RED    := \033[31m
GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
RESET  := \033[0m

# Project configuration
PROJECT_NAME := teach-me-mailer
DOCKER_IMAGE := $(PROJECT_NAME)
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

# Default target
help:
	@echo "$(GREEN)📧 Teach Me Mailer - Development Commands$(RESET)"
	@echo ""
	@echo "$(BLUE)🚀 Quick Start:$(RESET)"
	@echo "  $(YELLOW)make install$(RESET)     - Install all dependencies and setup environment"
	@echo "  $(YELLOW)make dev$(RESET)         - Start development server with hot reload"
	@echo ""
	@echo "$(BLUE)📦 Environment Management:$(RESET)"
	@echo "  $(YELLOW)make install$(RESET)     - Install Python dependencies and dev tools"
	@echo "  $(YELLOW)make check-env$(RESET)   - Verify environment configuration"
	@echo "  $(YELLOW)make pre-commit-install$(RESET) - Setup pre-commit hooks"
	@echo ""
	@echo "$(BLUE)🔧 Development:$(RESET)"
	@echo "  $(YELLOW)make dev$(RESET)         - Start development server (local Python)"
	@echo "  $(YELLOW)make migrate$(RESET)     - Run database migrations"
	@echo "  $(YELLOW)make reset-db$(RESET)    - Reset database and reseed (⚠️  destructive)"
	@echo ""
	@echo "$(BLUE)🐳 Docker Operations:$(RESET)"
	@echo "  $(YELLOW)make up$(RESET)          - Start all services with Docker Compose"
	@echo "  $(YELLOW)make down$(RESET)        - Stop all services"
	@echo "  $(YELLOW)make build$(RESET)       - Build Docker images"
	@echo "  $(YELLOW)make logs$(RESET)        - Show application logs"
	@echo "  $(YELLOW)make shell$(RESET)       - Open shell in running app container"
	@echo ""
		@echo "$(BLUE)🔍 Code Quality:$(RESET)"
		@echo "  $(YELLOW)make lint$(RESET)        - Run all linting checks (black, flake8, mypy)"
		@echo "  $(YELLOW)make format$(RESET)      - Auto-format code (black, isort)"
		@echo "  $(YELLOW)make security$(RESET)    - Run security scans (safety)"
	@echo ""
	@echo "$(BLUE)🗃️  Database:$(RESET)"
	@echo "  $(YELLOW)make db-shell$(RESET)    - Access PostgreSQL shell"
	@echo "  $(YELLOW)make db-backup$(RESET)   - Create database backup"
	@echo "  $(YELLOW)make db-status$(RESET)   - Show database status"
	@echo ""
	@echo "$(BLUE)🧪 Testing:$(RESET)"
	@echo "  $(YELLOW)make test$(RESET)        - Run all tests with coverage"
	@echo "  $(YELLOW)make test-unit$(RESET)   - Run unit tests only"
	@echo "  $(YELLOW)make test-integration$(RESET) - Run integration tests only"
	@echo "  $(YELLOW)make test-e2e$(RESET)    - Run end-to-end tests only"
	@echo "  $(YELLOW)make test-watch$(RESET)  - Run tests in watch mode"
	@echo "  $(YELLOW)make test-coverage$(RESET) - Generate coverage report"
	@echo "  $(YELLOW)make setup-test-db$(RESET) - Setup test database"
	@echo ""
	@echo "$(BLUE)📚 Documentation:$(RESET)"
	@echo "  $(YELLOW)make docs-serve$(RESET)  - Serve documentation locally"
	@echo "  $(YELLOW)make docs-build$(RESET)  - Build documentation"
	@echo ""
	@echo "$(BLUE)🚀 Deployment:$(RESET)"
	@echo "  $(YELLOW)make deploy-staging$(RESET) - Deploy to staging environment"
	@echo "  $(YELLOW)make deploy-prod$(RESET) - Deploy to production environment"
	@echo ""
	@echo "$(BLUE)🧹 Cleanup:$(RESET)"
	@echo "  $(YELLOW)make clean$(RESET)       - Clean up Docker containers and volumes"
	@echo ""

# Installation and setup
install:
	@echo "$(GREEN)📦 Installing dependencies and setting up environment...$(RESET)"
	python3 -m pip install --upgrade pip
	pip install -e ".[dev,test,docs]"
	@echo "$(GREEN)✅ Dependencies installed successfully$(RESET)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "1. Copy .env.example to .env and configure your settings"
	@echo "2. Run 'make migrate' to setup the database"
	@echo "3. Run 'make seed' to create a demo API key"
	@echo "4. Run 'make dev' to start the development server"

check-env:
	@echo "$(BLUE)🔍 Checking environment configuration...$(RESET)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found$(RESET)"; \
		echo "$(YELLOW)💡 Run: cp .env.example .env$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ .env file found$(RESET)"
	@python3 -c "from app.core.config import get_settings; get_settings()" 2>/dev/null && \
		echo "$(GREEN)✅ Configuration is valid$(RESET)" || \
		(echo "$(RED)❌ Configuration validation failed$(RESET)" && exit 1)

pre-commit-install:
	@echo "$(BLUE)🔧 Installing pre-commit hooks...$(RESET)"
	pre-commit install
	@echo "$(GREEN)✅ Pre-commit hooks installed$(RESET)"

# Development server
dev: check-env
	@echo "$(GREEN)🚀 Starting development server...$(RESET)"
	@echo "$(BLUE)📡 Server will be available at: http://localhost:8000$(RESET)"
	@echo "$(BLUE)📖 API docs available at: http://localhost:8000/docs$(RESET)"
	@echo "$(BLUE)📊 Metrics available at: http://localhost:8000/metrics$(RESET)"
	hui app.main:app --reload --host 0.0.0.0 --port 8000

# Database operations
migrate:
	@echo "$(BLUE)🗃️  Running database migrations...$(RESET)"
	alembic upgrade head
	@echo "$(GREEN)✅ Migrations completed$(RESET)"

seed:
	@echo "$(BLUE)🌱 Creating demo API key...$(RESET)"
	python3 scripts/demo_seed.py
	@echo "$(GREEN)✅ Demo API key created$(RESET)"

reset-db:
	@echo "$(RED)⚠️  This will delete all database data!$(RESET)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	@echo "$(BLUE)🗃️  Resetting database...$(RESET)"
	docker-compose down postgres || true
	docker volume rm $(PROJECT_NAME)_postgres_data || true
	docker-compose up -d postgres
	sleep 5
	make migrate
	make seed
	@echo "$(GREEN)✅ Database reset completed$(RESET)"

db-shell:
	@echo "$(BLUE)🗃️  Accessing PostgreSQL shell...$(RESET)"
	docker-compose exec postgres psql -U postgres -d mailgateway

db-backup:
	@echo "$(BLUE)🗃️  Creating database backup...$(RESET)"
	mkdir -p backups
	docker-compose exec postgres pg_dump -U postgres mailgateway > backups/backup-$(shell date +%Y%m%d-%H%M%S).sql
	@echo "$(GREEN)✅ Database backup created in backups/$(RESET)"

db-status:
	@echo "$(BLUE)🗃️  Database status:$(RESET)"
	docker-compose exec postgres pg_isready -U postgres && echo "$(GREEN)✅ Database is ready$(RESET)" || echo "$(RED)❌ Database not available$(RESET)"

# Docker operations
up:
	@echo "$(GREEN)🐳 Starting all services...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)✅ Services started$(RESET)"
	@echo ""
	@echo "$(BLUE)🌐 Available endpoints:$(RESET)"
	@echo "  📡 API Server: http://localhost:8000"
	@echo "  📖 API Docs: http://localhost:8000/docs"
	@echo "  📊 Metrics: http://localhost:8000/metrics"
	@echo "  🏥 Health: http://localhost:8000/health"

down:
	@echo "$(BLUE)🐳 Stopping all services...$(RESET)"
	docker-compose down
	@echo "$(GREEN)✅ Services stopped$(RESET)"

build:
	@echo "$(BLUE)🔨 Building Docker images...$(RESET)"
	docker-compose build --no-cache
	@echo "$(GREEN)✅ Images built successfully$(RESET)"

logs:
	@echo "$(BLUE)📋 Showing application logs...$(RESET)"
	docker-compose logs -f app

shell:
	@echo "$(BLUE)🐚 Opening shell in app container...$(RESET)"
	docker-compose exec app /bin/bash

# Code quality
lint:
	@echo "$(BLUE)🔍 Running code quality checks...$(RESET)"
	@echo "$(YELLOW)📝 Checking code formatting with Black...$(RESET)"
	black --check --diff app/ scripts/
	@echo "$(YELLOW)📚 Checking import sorting with isort...$(RESET)"
	isort --check-only --diff --skip scripts/generate_openapi.py app/ scripts/
	@echo "$(YELLOW)🔍 Linting with flake8...$(RESET)"
	flake8 app/ scripts/ --max-line-length=119 --extend-ignore=E203,W503 --exclude=scripts/generate_openapi.py
	@echo "$(YELLOW)🔍 Type checking with mypy...$(RESET)"
	mypy app/ --ignore-missing-imports
	@echo "$(GREEN)✅ All quality checks passed$(RESET)"

format:
	@echo "$(BLUE)✨ Auto-formatting code...$(RESET)"
	black --exclude 'scripts/generate_openapi.py' app/ scripts/
	isort --skip scripts/generate_openapi.py app/ scripts/
	@echo "$(GREEN)✅ Code formatted successfully$(RESET)"

security:
	@echo "$(BLUE)🔒 Running security scans...$(RESET)"
	@echo "$(YELLOW)🔍 Checking dependencies with Safety...$(RESET)"
	safety check --json --output safety-report.json || echo "$(YELLOW)⚠️  Vulnerable dependencies found - check safety-report.json$(RESET)"
	@echo "$(GREEN)✅ Security scan completed$(RESET)"

# Documentation
docs-serve:
	@echo "$(BLUE)📚 Serving documentation locally...$(RESET)"
	@echo "$(BLUE)📖 Documentation will be available at: http://localhost:8080$(RESET)"
	python3 -m http.server 8080 --directory docs/

docs-build:
	@echo "$(BLUE)📚 Building documentation...$(RESET)"
	python3 scripts/generate_openapi.py
	@echo "$(GREEN)✅ Documentation built successfully$(RESET)"

# Deployment
deploy-staging:
	@echo "$(BLUE)🚀 Deploying to staging environment...$(RESET)"
	@echo "$(YELLOW)⚠️  Make sure you have configured staging secrets$(RESET)"
	docker-compose -f docker-compose.staging.yml up -d --build
	@echo "$(GREEN)✅ Deployed to staging$(RESET)"

deploy-prod:
	@echo "$(BLUE)🚀 Deploying to production environment...$(RESET)"
	@echo "$(RED)⚠️  This will deploy to production!$(RESET)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose -f docker-compose.prod.yml up -d --build
	@echo "$(GREEN)✅ Deployed to production$(RESET)"

# Cleanup
clean:
	@echo "$(BLUE)🧹 Cleaning up Docker containers and volumes...$(RESET)"
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)✅ Cleanup completed$(RESET)"

# Utility targets
docker-build:
	@echo "$(BLUE)🔨 Building Docker image: $(DOCKER_IMAGE):$(VERSION)$(RESET)"
	docker build -t $(DOCKER_IMAGE):$(VERSION) -t $(DOCKER_IMAGE):latest .

docker-push:
	@echo "$(BLUE)📤 Pushing Docker image: $(DOCKER_IMAGE):$(VERSION)$(RESET)"
	docker push $(DOCKER_IMAGE):$(VERSION)
	docker push $(DOCKER_IMAGE):latest

# Check rate limits
check-limits:
	@echo "$(BLUE)📊 Checking rate limit status...$(RESET)"
	docker-compose exec postgres psql -U postgres -d mailgateway -c "
	SELECT k.name, k.daily_limit,
	       COALESCE(u.count, 0) as used_today,
	       (k.daily_limit - COALESCE(u.count, 0)) as remaining
	FROM api_keys k
	LEFT JOIN daily_usage u ON k.id = u.api_key_id AND u.date = CURRENT_DATE
	WHERE k.is_active = true;
	"

# Testing commands
setup-test-db:
	@echo "$(BLUE)🗃️  Setting up test database...$(RESET)"
	python3 scripts/setup_test_db.py
	@echo "$(GREEN)✅ Test database ready$(RESET)"

test: check-env
	@echo "$(BLUE)🧪 Running all tests with coverage...$(RESET)"
	pytest --cov=app --cov-report=html --cov-report=xml --cov-report=term-missing
	@echo "$(GREEN)✅ Tests completed$(RESET)"
	@echo "$(BLUE)📊 Coverage report: htmlcov/index.html$(RESET)"

test-unit:
	@echo "$(BLUE)🧪 Running unit tests...$(RESET)"
	pytest tests/unit/ -v
	@echo "$(GREEN)✅ Unit tests completed$(RESET)"

test-integration:
	@echo "$(BLUE)🧪 Running integration tests...$(RESET)"
	pytest tests/integration/ -v
	@echo "$(GREEN)✅ Integration tests completed$(RESET)"

test-e2e:
	@echo "$(BLUE)🧪 Running end-to-end tests...$(RESET)"
	pytest tests/e2e/ -v
	@echo "$(GREEN)✅ E2E tests completed$(RESET)"

test-watch:
	@echo "$(BLUE)🧪 Running tests in watch mode...$(RESET)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(RESET)"
	pytest-watch -- -v

test-coverage:
	@echo "$(BLUE)📊 Generating coverage report...$(RESET)"
	pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✅ Coverage report generated$(RESET)"
	@echo "$(BLUE)📂 Opening coverage report...$(RESET)"
	open htmlcov/index.html || xdg-open htmlcov/index.html

test-fast:
	@echo "$(BLUE)⚡ Running tests in parallel (fast mode)...$(RESET)"
	pytest -n auto --maxfail=1 -q
	@echo "$(GREEN)✅ Fast tests completed$(RESET)"

test-smoke:
	@echo "$(BLUE)🔥 Running smoke tests...$(RESET)"
	pytest tests/test_smoke.py -v
	@echo "$(GREEN)✅ Smoke tests passed$(RESET)"

test-clean:
	@echo "$(BLUE)🧹 Cleaning test artifacts...$(RESET)"
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	@echo "$(GREEN)✅ Test artifacts cleaned$(RESET)"
