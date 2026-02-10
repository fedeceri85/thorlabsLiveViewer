#!/bin/bash
# Thorlabs Live Viewer Startup Script for Linux/macOS
# This script activates the virtual environment and starts the GUI

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo " Thorlabs Live Viewer Startup"
echo "========================================"
echo ""

# Check for .venv directory
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment '.venv' not found."
    echo "Please run the setup script or create it manually:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[1/2] Activating virtual environment..."
source .venv/bin/activate

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Environment activated successfully."
echo ""

echo "[2/2] Starting Thorlabs Live Viewer GUI..."
echo ""

# Start the GUI application
python thorlabs_gui_app.py

# Check exit code
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Program exited with error code $?"
    echo ""
    read -p "Press Enter to exit..."
else
    echo ""
    echo "Program closed successfully."
fi

echo ""
deactivate
echo "Done."
