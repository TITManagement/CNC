# Makefile - common development shortcuts for CNC project

.PHONY: setup dev-setup help
 .PHONY: platform-setup

help:
	@echo "Makefile targets:"
	@echo "  setup      - Create .venv and install dependencies"
	@echo "  dev-setup  - Create .venv and install dev dependencies (if available)"

setup:
	@echo "Running setup script..."
	@bash ./dev/scripts/setup.sh

dev-setup:
	@echo "Running setup script with development dependencies..."
	@bash ./dev/scripts/setup.sh --dev

platform-setup:
	@echo "Running cross-platform setup via package entry point..."
	@python3 -m cnc_tools.setup_platform
