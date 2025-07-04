.PHONY: help install test format clean

help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-15s %s\n", $$1, $$2}'

install:  ## Install package in development mode
	pip install -e ".[dev]"

test:  ## Run tests
	python -m pytest tests/ -v

format:  ## Format code
	black . && isort .

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/ .mypy_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 