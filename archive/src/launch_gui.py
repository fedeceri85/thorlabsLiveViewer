#!/usr/bin/env python3
"""
Thorlabs GUI Launcher
=====================

Simple launcher for the Thorlabs Live Viewer GUI with options to
generate test data if needed.

Usage:
    python launch_gui.py [--generate-test]

Author: AI Assistant
Date: August 2025
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def generate_test_data():
    """Generate test data for demonstration"""
    print("🎬 Generating test data for GUI demonstration...")
    
    test_dir = Path("../testLiveData")
    
    # Run the generator
    cmd = [
        sys.executable, "generate_live_raw.py",
        "--output-dir", str(test_dir),
        "--frames", "200",
        "--fps", "2.0",
        "--width", "512",
        "--height", "512"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Test data generated successfully!")
        print(f"📂 Location: {test_dir.absolute()}")
        return str(test_dir.absolute())
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating test data: {e}")
        print(f"❌ Output: {e.stderr}")
        return None


def launch_gui(initial_folder=None):
    """Launch the GUI application"""
    print("🚀 Launching Thorlabs Live Viewer GUI...")
    
    cmd = [sys.executable, "thorlabs_gui_app.py"]
    if initial_folder:
        cmd.append(initial_folder)
    
    try:
        # Launch GUI (non-blocking)
        subprocess.Popen(cmd)
        print("✅ GUI launched successfully!")
        print("💡 The GUI window should appear shortly")
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Launch Thorlabs Live Viewer GUI")
    parser.add_argument("--generate-test", action="store_true",
                        help="Generate test data before launching GUI")
    parser.add_argument("--folder", type=str,
                        help="Initial folder to open in GUI")
    
    args = parser.parse_args()
    
    initial_folder = args.folder
    
    # Generate test data if requested
    if args.generate_test:
        initial_folder = generate_test_data()
        if not initial_folder:
            print("❌ Failed to generate test data, launching GUI anyway...")
            initial_folder = None
    
    # Launch GUI
    launch_gui(initial_folder)
    
    print("\n" + "="*50)
    print("🎮 GUI Features:")
    print("="*50)
    print("📂 Browse and select data folders")
    print("⚙️  Adjust monitoring parameters")
    print("🚀 Start/stop/restart monitoring")
    print("📊 Real-time progress tracking")
    print("📋 Status logging")
    print("🔄 Automatic reset for new folders")
    print("="*50)


if __name__ == "__main__":
    main()
