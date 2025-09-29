.PHONY: help install test lint format run build dev clean docker-build docker-run docker-dev

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies with uv"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black"
	@echo "  run         - Run the application"
	@echo "  build       - Build Docker image"
	@echo "  dev         - Run development environment"
	@echo "  clean       - Clean up temporary files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run Docker container"
	@echo "  docker-dev  - Run development Docker container"

# Development commands
install:
	uv sync --dev

test:
	uv run pytest tests/ -v

lint:
	uv run flake8 app.py services/ models/ core/
	uv run black --check app.py services/ models/ core/
	uv run mypy app.py services/ models/ core/

format:
	uv run black app.py services/ models/ core/

run:
	uv run python app.py

# Docker commands
docker-build:
	docker build -t omex-coin-sniper-api:latest .

docker-run:
	docker-compose up -d

docker-dev:
	docker-compose -f docker-compose.dev.yml up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Development environment
dev: install
	uv run python app.py

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/

# Production deployment
deploy:
	docker-compose up -d --build

# Health check
health:
	curl -f http://localhost:8000/api/v1/health/ping || exit 1
