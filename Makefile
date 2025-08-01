.PHONY: help install install-dev test lint format clean build run debug

help: ## Show this help message
	@echo "TRUMPF Oseon MCP Server - Development Commands"
	@echo "================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package in development mode
	pip install -e .

install-dev: ## Install the package with development dependencies
	pip install -e ".[dev]"

test: ## Run the test suite
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ --cov=src/trumpf_oseon_mcp --cov-report=html --cov-report=term

lint: ## Run linting checks
	flake8 src/ tests/
	mypy src/

format: ## Format code with black
	black src/ tests/

format-check: ## Check if code is formatted correctly
	black --check src/ tests/

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: ## Build the package
	python -m build

run: ## Run the MCP server
	python -m trumpf_oseon_mcp

debug: ## Run the debug script
	python tools/debug_api.py

test-server: ## Run the test server script
	python tests/test_server.py

setup-env: ## Set up the development environment
	python -m venv .venv
	@echo "Virtual environment created. Activate it with:"
	@echo "source .venv/bin/activate  # On macOS/Linux"
	@echo "or"
	@echo ".venv\\Scripts\\activate  # On Windows"

check: format-check lint test ## Run all checks (format, lint, test)

pre-commit: format lint test ## Run pre-commit checks

release: clean build ## Build release package
	@echo "Release package built in dist/ directory" 