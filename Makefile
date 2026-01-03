.PHONY: help install test format clean check-size check-coverage pre-commit-install

help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

install:  ## Install package in development mode
	pip install -e ".[dev]"

test:  ## Run tests
	python -m pytest tests/ -v

test-integration:  ## Run integration tests only
	python -m pytest tests/test_integration.py -v

test-unit:  ## Run unit tests only
	python -m pytest tests/ -v --ignore=tests/test_integration.py

test-cov:  ## Run tests with coverage report
	python -m pytest tests/ -v --cov=cursor_chronicle --cov=search_history --cov-report=term-missing --cov-report=html

format:  ## Format code with black and isort
	black . && isort .

check-size:  ## Check Python file sizes (max 400 lines)
	python scripts/check_file_size.py $$(find . -name "*.py" -not -path "./.venv/*" -not -path "./build/*")

check-coverage:  ## Check test coverage meets threshold
	python scripts/check_coverage.py

pre-commit-install:  ## Install pre-commit hooks
	pip install pre-commit && pre-commit install && pre-commit install --hook-type pre-push

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/ .mypy_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
