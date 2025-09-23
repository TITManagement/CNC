#!/bin/bash
# Setup script for CNC XY Runner development environment
# Usage: ./scripts/setup.sh

set -e

echo "🚀 Setting up CNC XY Runner development environment..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "📈 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies (optional)
if [ "$1" = "--dev" ] || [ "$1" = "-d" ]; then
    echo "🛠️  Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Install package in editable mode for development
echo "📦 Installing package in editable mode..."
pip install -e .

echo "✅ Setup complete!"
echo ""
echo "To activate the environment manually:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the CNC XY Runner:"
echo "  python src/xy_runner.py examples/job_svg.yaml"
echo ""
echo "Or use the installed command:"
echo "  cnc-xy-runner examples/job_svg.yaml"