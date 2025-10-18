# Makefile - common development shortcuts for CNC project

.PHONY: setup dev-setup help

help:
	@echo "Makefile targets:"
	@echo "  setup      - Create .venv and install dependencies"
	@echo "  dev-setup  - Create .venv and install dev dependencies (if available)"

setup:
	@echo "Running setup script..."
	@bash ./scripts/setup.sh

dev-setup:
	@echo "Running setup script with development dependencies..."
	@bash ./scripts/setup.sh --dev
