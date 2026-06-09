#!/bin/bash
# Thorlabs Live Viewer Startup Script for Mac

cd "$(dirname "$0")"

echo "========================================"
echo " Thorlabs Live Viewer Startup"
echo "========================================"
echo ""

if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found."
    echo "Please double-click 'setup_mac.command' first to install the software."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

source .venv/bin/activate

echo "Starting Thorlabs Live Viewer GUI..."
python3 thorlabs_gui_app.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Program exited with an error."
    read -p "Press Enter to exit..."
fi
