#!/bin/bash
# Thorlabs Live Viewer Setup for Mac

cd "$(dirname "$0")"

echo "========================================"
echo " Thorlabs Live Viewer Setup (Mac)"
echo "========================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 could not be found."
    echo "Please install Python from python.org"
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Installing dependencies..."
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "========================================"
echo "SETUP COMPLETE!"
echo "You can now double-click 'start_mac.command' to launch the app."
echo "========================================"
read -p "Press Enter to close..."
