#!/usr/bin/env python3
"""
Quick Launcher for Thorlabs Live Viewer
=======================================

This script helps you quickly test the live viewer with your existing data
or generate test data for real-time monitoring.

Usage Examples:
    python quick_test.py                    # Use existing sampleImage data
    python quick_test.py --generate-test    # Generate test data first
    python quick_test.py /path/to/data      # Use specific data folder
"""

import os
import sys
import subprocess
import argparse
import time

def main():
    parser = argparse.ArgumentParser(description="Quick launcher for Thorlabs Live Viewer")
    parser.add_argument("folder", nargs='?', default="../sampleImage",
                        help="Path to data folder")
    parser.add_argument("--generate-test", action="store_true",
                        help="Generate test data first")
    parser.add_argument("--test-frames", type=int, default=100,
                        help="Number of test frames to generate (default: 100)")
    parser.add_argument("--test-fps", type=float, default=2.0,
                        help="Test data generation FPS (default: 2.0)")
    
    args = parser.parse_args()
    
    if args.generate_test:
        print("🎬 Generating test data for live monitoring...")
        
        # Create test directory
        test_dir = "../testLiveData"
        os.makedirs(test_dir, exist_ok=True)
        
        # Generate test data
        cmd = [
            "python", "generate_live_raw.py",
            "--output-dir", test_dir,
            "--frames", str(args.test_frames),
            "--fps", str(args.test_fps),
            "--width", "512",
            "--height", "512"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        # Start generator in background
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait a moment for file creation
            time.sleep(2)
            
            # Check if files were created
            raw_file = os.path.join(test_dir, "Image_001_001.raw")
            preview_file = os.path.join(test_dir, "ChanC_Preview.tif")
            
            if os.path.exists(raw_file) and os.path.exists(preview_file):
                print("✅ Test files created successfully!")
                print(f"📂 Test data location: {test_dir}")
                
                # Update folder to use test data
                args.folder = test_dir
                
                print("🎯 Starting live viewer in 3 seconds...")
                print("💡 The generator will continue writing frames in the background")
                time.sleep(3)
                
            else:
                print("❌ Failed to create test files")
                return 1
                
        except Exception as e:
            print(f"❌ Error generating test data: {e}")
            return 1
    
    # Check if data folder exists
    if not os.path.exists(args.folder):
        print(f"❌ Error: Data folder not found: {args.folder}")
        print("💡 Try using --generate-test to create test data")
        return 1
    
    # Check for required files
    raw_file = os.path.join(args.folder, "Image_001_001.raw")
    preview_file = os.path.join(args.folder, "ChanC_Preview.tif")
    
    if not os.path.exists(raw_file):
        print(f"❌ Error: Raw file not found: {raw_file}")
        return 1
    
    if not os.path.exists(preview_file):
        print(f"❌ Error: Preview file not found: {preview_file}")
        return 1
    
    print(f"🚀 Launching Thorlabs Live Viewer...")
    print(f"📂 Data folder: {args.folder}")
    
    # Launch the live viewer
    cmd = ["python", "thorlabs_live_viewer.py", args.folder]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error running live viewer: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
