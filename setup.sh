#!/bin/bash
# LCA-Copilot Single-Click Setup & Launcher Script

echo "================================================================================"
echo "                   LCA-COPILOT ONE-CLICK INSTALLER & LAUNCHER"
echo "================================================================================"

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Create virtual environment if it does not exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

# 2. Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing requirements from requirements.txt..."
pip install -r requirements.txt

# 4. Run system diagnostics
echo "Running system diagnostics..."
python3 -m agentic_lca.cli --setup

echo "================================================================================"
echo "Setup complete! To run the interactive chat CLI, use:"
echo "  source .venv/bin/activate && python3 run_pipeline.py --chat"
echo ""
echo "To run the Web Dashboard, use:"
echo "  source .venv/bin/activate && python3 run_pipeline.py --web"
echo "================================================================================"
