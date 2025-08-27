#!/usr/bin/env python3
"""
Thorlabs Live Viewer - Simple Version
=====================================

Simplified version with focus on macOS compatibility and threading safety.
This version uses a more conservative approach to GUI updates.

Usage:
    python thorlabs_live_viewer_simple.py [path_to_data_folder]

Author: AI Assistant
Date: August 2025
"""

import os
import sys
import threading
import time
import numpy as np
import argparse
from os.path import getsize
from qtpy.QtCore import QTimer, QObject, Signal

# Import GPU libraries
if sys.platform != 'darwin':
    from cupyx.scipy.ndimage import gaussian_filter
    import cupy as cp
else:
    from scipy.ndimage import gaussian_filter
    try:
        import pyclesperanto_prototype as cle
    except:
        cle = None

import napari
from skimage.io import imread

# Constants
FILENAME = 'Image_001_001.raw'
PREVIEW_FILENAME = 'ChanC_Preview.tif'


class DataUpdater(QObject):
    """Qt object for thread-safe communication"""
    data_ready = Signal(np.ndarray)


class ThorlabsLiveViewerSimple:
    """Simplified real-time viewer with robust macOS threading"""
    
    def __init__(self, folder):
        """Initialize the live viewer"""
        print(f"🔬 Initializing Simple Thorlabs Live Viewer")
        
        # Setup GPU if available
        if sys.platform == 'darwin' and cle:
            try:
                device = cle.select_device("GTX")
                print(f"🚀 GPU: {device}")
            except:
                print("⚠️  GPU not available, using CPU")
        else:
            print("🚀 Using CPU processing")
        
        self.folder = folder
        self.fullpath = os.path.join(self.folder, FILENAME)
        
        # Load preview to get dimensions
        preview_path = os.path.join(self.folder, PREVIEW_FILENAME)
        if not os.path.exists(preview_path):
            raise FileNotFoundError(f"Preview file not found: {preview_path}")
        
        prev = imread(preview_path)
        self.width = prev.shape[1]
        self.height = prev.shape[0]
        
        # Open raw file
        if not os.path.exists(self.fullpath):
            raise FileNotFoundError(f"Raw file not found: {self.fullpath}")
            
        self.r = open(self.fullpath, 'rb')
        nbytes = getsize(self.fullpath)
        self.frameSize = self.width * self.height * 2
        self.nFrames = int(nbytes / self.frameSize)
        
        print(f"📊 File info: {self.width}x{self.height}, {self.nFrames} frames ({nbytes/1024/1024:.1f} MB)")
        
        # Initialize data arrays
        self.currentLastFrame = 0
        self.array = np.empty((0, self.height, self.width), dtype=np.uint16)
        
        # Threading control
        self.stop_flag = threading.Event()
        self.monitoring_active = False
        self.data_lock = threading.Lock()
        
        # Qt-based updater
        self.updater = DataUpdater()
        self.updater.data_ready.connect(self._update_viewer_main_thread)
        
        # Create Napari viewer (main thread only)
        self.app = napari.Viewer(title=f"Simple Thorlabs Live Viewer - {os.path.basename(folder)}")
        self.image_layer = None
        
        print("✅ Initialization complete")
    
    def getImage(self, n):
        """Load a single frame"""
        offset = n * self.frameSize
        self.r.seek(offset)
        st = self.r.read(self.frameSize)
        nparray = np.frombuffer(st, dtype=np.uint16).reshape((1, self.height, self.width))
        return nparray
    
    def loadFrameChunk(self, start, end):
        """Load a chunk of frames (simplified)"""
        if start >= end or start < 0 or end > self.nFrames:
            return None
        
        totalFrames = end - start
        totalFramesSize = totalFrames * self.frameSize
        
        offset = start * self.frameSize
        self.r.seek(offset)
        st = self.r.read(totalFramesSize)
        
        if len(st) < totalFramesSize:
            # Partial read
            actual_frames = len(st) // self.frameSize
            if actual_frames == 0:
                return None
            totalFrames = actual_frames
        
        stack = np.frombuffer(st, dtype=np.uint16).reshape((totalFrames, self.height, self.width))
        
        # Basic processing (no GPU for simplicity)
        return stack
    
    def start_live_monitoring(self, chunk_size=3, wait_time=0.3):
        """Start live monitoring with simple background thread"""
        if self.monitoring_active:
            print("⚠️  Monitoring already active")
            return
        
        self.monitoring_active = True
        self.stop_flag.clear()
        
        print(f"🎬 Starting simple live monitoring:")
        print(f"   • Chunk size: {chunk_size} frames")
        print(f"   • Wait time: {wait_time}s at live edge")
        print(f"   • Total frames allocated: {self.nFrames}")
        
        def monitoring_thread():
            """Simple background monitoring thread"""
            current_frame = self.currentLastFrame
            consecutive_zeros = 0
            
            print("🚀 Simple monitoring thread started")
            
            while not self.stop_flag.is_set():
                try:
                    # Check if we've reached the end
                    if current_frame >= self.nFrames:
                        print("🏁 Reached end of allocated file space")
                        break
                    
                    # Load next chunk
                    end_frame = min(current_frame + chunk_size, self.nFrames)
                    new_block = self.loadFrameChunk(current_frame, end_frame)
                    
                    if new_block is None:
                        time.sleep(wait_time)
                        continue
                    
                    # Check for black frames (live edge)
                    zero_idx = None
                    for i, frame in enumerate(new_block):
                        if np.all(frame == 0):
                            zero_idx = i
                            break
                    found_zeros = False
                    if zero_idx is not None:
                        if zero_idx > 0:
                            # Partial data
                            new_block = new_block[:zero_idx]
                            consecutive_zeros = 0
                            found_zeros = True
                        else:
                            # All black frames - at live edge
                            consecutive_zeros += 1
                            if consecutive_zeros % 10 == 1:  # Log every 10th attempt
                                print(f"⏸️  At live edge (frame {current_frame}) - waiting {wait_time:.1f}s...")
                            time.sleep(wait_time)
                            continue
                    else:
                        consecutive_zeros = 0
                    
                    # Update data arrays (thread-safe)
                    if new_block.size > 0:
                        with self.data_lock:
                            self.array = np.vstack([self.array, new_block])
                            current_frame += new_block.shape[0]
                            self.currentLastFrame = self.array.shape[0]
                            data_copy = self.array.copy()
                        
                        # Signal GUI update (thread-safe Qt signal)
                        self.updater.data_ready.emit(data_copy)
                        
                        print(f"📈 Loaded {new_block.shape[0]} frames, total: {self.currentLastFrame}")
                    
                    # Small pause to prevent overload
                    time.sleep(0.05)
                    if found_zeros:
                        time.sleep(wait_time)
                        found_zeros = False

                except Exception as e:
                    print(f"❌ Error in monitoring thread: {e}")
                    import traceback
                    traceback.print_exc()
                    break
            
            self.monitoring_active = False
            print("🛑 Simple monitoring stopped")
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=monitoring_thread, daemon=True)
        self.monitor_thread.start()
        
        print("✅ Live monitoring started! Press Ctrl+C to stop")
    
    def _update_viewer_main_thread(self, data):
        """Update viewer on main thread via Qt signal"""
        try:
            if self.image_layer is None:
                # Create layer first time
                self.image_layer = self.app.add_image(data, name='Live Stream')
                
                # Add shapes layer for annotations
                try:
                    self.app.add_shapes(
                        None, shape_type='rectangle', name='Annotations',
                        edge_width=3, face_color=np.array([0, 0, 0, 0]),
                        edge_color='red'
                    )
                except:
                    pass  # Shapes might already exist
            else:
                # Update existing layer
                self.image_layer.data = data
                
        except Exception as e:
            print(f"⚠️  Viewer update error: {e}")
    
    def stop_monitoring(self):
        """Stop the live monitoring"""
        if self.monitoring_active:
            print("🛑 Stopping live monitoring...")
            self.stop_flag.set()
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join(timeout=2)
            print("✅ Monitoring stopped")
        else:
            print("ℹ️  Monitoring not active")
    
    def get_status(self):
        """Get current monitoring status"""
        status = "🟢 Active" if self.monitoring_active else "🔴 Inactive"
        remaining = self.nFrames - self.currentLastFrame
        
        print(f"📊 Status: {status}")
        print(f"📈 Frames loaded: {self.currentLastFrame}/{self.nFrames}")
        print(f"⏳ Remaining: {remaining} frames")
        
        return {
            'active': self.monitoring_active,
            'frames_loaded': self.currentLastFrame,
            'total_frames': self.nFrames,
            'remaining': remaining
        }
    
    def restart_monitoring(self, chunk_size=3, wait_time=0.3):
        """Restart monitoring with new parameters"""
        self.stop_monitoring()
        time.sleep(0.5)  # Brief pause
        self.start_live_monitoring(chunk_size, wait_time)
    
    def run_interactive(self):
        """Run interactive mode with controls"""
        print("\n" + "="*50)
        print("🎮 Simple Live Viewer Controls")
        print("="*50)
        print("Commands:")
        print("  's' + Enter: Show status")
        print("  'r' + Enter: Restart monitoring")
        print("  'q' + Enter: Quit")
        print("  Ctrl+C: Force quit")
        print("="*50)
        
        try:
            while True:
                command = input().strip().lower()
                
                if command == 's':
                    self.get_status()
                elif command == 'r':
                    self.restart_monitoring()
                elif command == 'q':
                    break
                else:
                    print("❓ Unknown command. Use 's', 'r', or 'q'")
                    
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self.stop_monitoring()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Simple Thorlabs Live Viewer')
    parser.add_argument('folder', nargs='?', default='../testLiveData',
                        help='Path to data folder (default: ../testLiveData)')
    parser.add_argument('--chunk-size', type=int, default=3,
                        help='Frames to load per chunk (default: 3)')
    parser.add_argument('--wait-time', type=float, default=0.3,
                        help='Wait time at live edge in seconds (default: 0.3)')

    
    args = parser.parse_args()
    
    try:
        # Initialize viewer
        viewer = ThorlabsLiveViewerSimple(args.folder)
        
        # Start monitoring
        viewer.start_live_monitoring(
            chunk_size=args.chunk_size,
            wait_time=args.wait_time
        )
        
        # Show initial status
        viewer.get_status()
        
        # Run interactive mode
        viewer.run_interactive()
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
