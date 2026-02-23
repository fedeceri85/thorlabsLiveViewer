#!/usr/bin/env python3
"""
Thorlabs Live Viewer
====================

Real-time viewer for Thorlabs microscopy data with background threading
that actually works properly (not limited by Jupyter notebooks).

This script provides live monitoring of raw files being written in real-time,
with automatic Napari viewer updates in the background.

Usage:
    python thorlabs_live_viewer.py [path_to_data_folder]

Author: AI Assistant
Date: August 2025
"""

import os
import gc
import sys
import matplotlib.pyplot as plt
import threading
import time
import numpy as np
import argparse
from os.path import getsize
from qtpy.QtCore import QTimer

# Import GPU libraries
if sys.platform != 'darwin':
    from cupyx.scipy.ndimage import gaussian_filter
    import cupy as cp
else:
    from scipy.ndimage import gaussian_filter
    import pyclesperanto_prototype as cle

import napari
from skimage.io import imread

# Constants
FILENAME = 'Image_001_001.raw'
PREVIEW_FILENAME = 'ChanC_Preview.tif'

MAXCHUNKSIZE = 1024 * 288 * 2 * 3


class ThorlabsLiveViewer:
    """Real-time viewer for Thorlabs microscopy data with proper threading"""
    
    def __init__(self, folder):
        """Initialize the live viewer"""
        print(f"🔬 Initializing Thorlabs Live Viewer")
        
        # Setup GPU if available
        if sys.platform == 'darwin':
            try:
                device = cle.select_device("GTX")
                print(f"🚀 GPU: {device}")
            except:
                print("⚠️  GPU not available, using CPU")
        else:
            print("🚀 Using CUDA acceleration")
        
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
        
        # Create Napari viewer
        self.app = napari.Viewer(title=f"Thorlabs Live Viewer - {os.path.basename(folder)}")
        
        # Threading control
        self.stop_flag = threading.Event()
        self.monitoring_active = False
        self.data_lock = threading.Lock()
        self.update_pending = False
        
        # Qt timer for thread-safe viewer updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_viewer_from_timer)
        self.update_timer.start(100)  # Update every 100ms
        
        print("✅ Initialization complete")
    
    def getImage(self, n):
        """Load a single frame"""
        offset = n * self.frameSize
        self.r.seek(offset)
        st = self.r.read(self.frameSize)
        nparray = np.frombuffer(st, dtype=np.uint16).reshape((1, self.height, self.width))
        return nparray
    
    def loadWholeStack(self, start=0, end=-1, step=1):
        """Load a stack of frames with GPU acceleration"""
        if end == -1:
            end = self.nFrames
        
        # Validation
        if start >= end or start < 0 or end > self.nFrames:
            print(f"❌ Invalid frame range: start={start}, end={end}, nFrames={self.nFrames}")
            return []
        
        totalFrames = end - start
        totalFramesSize = totalFrames * self.frameSize
        
        if totalFramesSize <= MAXCHUNKSIZE:
            # Small chunk - load all at once
            offset = start * self.frameSize
            self.r.seek(offset)
            st = self.r.read(totalFramesSize)
            
            if sys.platform != 'darwin':
                # CUDA processing
                stack = cp.frombuffer(st, dtype=np.uint16).reshape((totalFrames, self.height, self.width))
                stack = stack[::, :, :]
                stack = gaussian_filter(stack, (2, 2, 2))
                stack3 = [cp.asnumpy(stack)]
            else:
                # OpenCL processing
                stack = np.frombuffer(st, dtype=np.uint16).reshape((totalFrames, self.height, self.width))
                stack = stack[::2, :, :]
                stack = cle.gaussian_blur(stack, sigma_x=2, sigma_y=2, sigma_z=2).astype(np.uint16)
                stack3 = [stack]
        else:
            # Large chunk - process in pieces
            chunksizeFrames = MAXCHUNKSIZE // self.frameSize
            nchunks = totalFrames // chunksizeFrames
            remainderFrames = totalFrames % chunksizeFrames
            stack3 = []
            
            for i in range(nchunks):
                offset = (start + i * chunksizeFrames) * self.frameSize
                self.r.seek(offset)
                st = self.r.read(self.frameSize * chunksizeFrames)
                
                if sys.platform != 'darwin':
                    stack = cp.frombuffer(st, dtype=np.uint16).reshape((chunksizeFrames, self.height, self.width))
                    stack = stack[::, :, :]
                    stack = gaussian_filter(stack, (2, 2, 2))
                    stack3.append(cp.asnumpy(stack))
                else:
                    stack = np.frombuffer(st, dtype=np.uint16).reshape((chunksizeFrames, self.height, self.width))
                    stack = stack[::2, :, :]
                    stack = cle.gaussian_blur(stack, sigma_x=2, sigma_y=2, sigma_z=2).astype(np.uint16)
                    stack3.append(stack)
            
            if remainderFrames != 0:
                offset = (start + nchunks * chunksizeFrames) * self.frameSize
                self.r.seek(offset)
                st = self.r.read(self.frameSize * remainderFrames)
                
                if sys.platform != 'darwin':
                    stack = cp.frombuffer(st, dtype=np.uint16).reshape((remainderFrames, self.height, self.width))
                    stack = stack[::, :, :]
                    stack = gaussian_filter(stack, (2, 2, 2))
                    stack3.append(cp.asnumpy(stack))
                else:
                    stack = np.frombuffer(st, dtype=np.uint16).reshape((remainderFrames, self.height, self.width))
                    stack = stack[::, :, :]
                    stack = cle.gaussian_blur(stack, sigma_x=2, sigma_y=2, sigma_z=2).astype(np.uint16)
                    stack3.append(stack)
        
        # Clean up GPU memory
        if sys.platform != 'darwin':
            cp._default_memory_pool.free_all_blocks()
        
        return stack3
    
    def start_live_monitoring(self, chunk_size=10, wait_time=1.0, fps=15):
        """Start real-time monitoring with background threading"""
        if self.monitoring_active:
            print("⚠️  Monitoring already active!")
            return
        
        print(f"🎬 Starting live monitoring:")
        print(f"   • Chunk size: {chunk_size} frames")
        print(f"   • Wait time: {wait_time}s at live edge")
        print(f"   • Expected FPS: {fps}")
        print(f"   • Total frames allocated: {self.nFrames}")
        
        self.stop_flag.clear()
        self.monitoring_active = True
        
        def monitoring_thread():
            """Background thread for continuous monitoring"""
            current_frame = self.currentLastFrame
            consecutive_zeros = 0
            
            print("🚀 Background monitoring thread started")
            
            while not self.stop_flag.is_set():
                try:
                    # Check if we've reached the end
                    if current_frame >= self.nFrames:
                        print("🏁 Reached end of allocated file space")
                        break
                    
                    # Load next chunk
                    end_frame = min(current_frame + chunk_size, self.nFrames)
                    
                    newStacks = self.loadWholeStack(start=current_frame, end=end_frame)
                    if not newStacks:
                        time.sleep(wait_time)
                        continue
                    
                    new_block = np.vstack(newStacks)
                    
                    # Check for black frames (live edge)
                    zero_idx = None
                    for i, frame in enumerate(new_block):
                        if np.all(frame == 0):
                            zero_idx = i
                            break
                    
                    if zero_idx is not None:
                        if zero_idx > 0:
                            # Partial data
                            new_block = new_block[:zero_idx]
                            consecutive_zeros = 0
                        else:
                            # All black frames - at live edge
                            consecutive_zeros += 1
                            adaptive_wait = min(wait_time, (chunk_size / fps) * 1.5) if fps > 0 else wait_time
                            
                            if consecutive_zeros % 10 == 1:  # Log every 10th attempt
                                print(f"⏸️  At live edge (frame {current_frame}) - waiting {adaptive_wait:.1f}s...")
                            
                            time.sleep(adaptive_wait)
                            continue
                    else:
                        consecutive_zeros = 0
                    
                    # Update data arrays (thread-safe)
                    if new_block.size > 0:
                        with self.data_lock:
                            self.array = np.vstack([self.array, new_block])
                            current_frame += new_block.shape[0]
                            self.currentLastFrame = self.array.shape[0]
                        
                        # Signal for viewer update (thread-safe)
                        self.update_pending = True
                        
                        print(f"📈 Loaded {new_block.shape[0]} frames, total: {self.currentLastFrame}")
                    
                    # Small pause to prevent overload
                    time.sleep(0.05)
                    
                except Exception as e:
                    print(f"❌ Error in monitoring thread: {e}")
                    import traceback
                    traceback.print_exc()
                    break
            
            self.monitoring_active = False
            print("🛑 Background monitoring stopped")
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=monitoring_thread, daemon=True)
        self.monitor_thread.start()
        
        print("✅ Live monitoring started! Press Ctrl+C to stop")
    
    def _update_viewer_from_timer(self):
        """Timer-based viewer updates (runs on main thread)"""
        if self.update_pending:
            try:
                with self.data_lock:
                    if self.array.size > 0:
                        # Update existing layer or create new one
                        if hasattr(self.app, 'layers') and len(self.app.layers) > 0:
                            # Find existing image layer
                            for layer in self.app.layers:
                                if hasattr(layer, 'data'):
                                    layer.data = self.array.copy()
                                    break
                        else:
                            # Create new layer (first time)
                            self.app.add_image(self.array.copy(), name='Live Stream')
                            
                            # Add shapes layer for annotations
                            try:
                                self.app.add_shapes(
                                    None, shape_type='rectangle', name='Annotations',
                                    edge_width=3, face_color=np.array([0, 0, 0, 0]),
                                    edge_color='red'
                                )
                            except:
                                pass  # Shapes might already exist
                        
                        self.update_pending = False
                        
            except Exception as e:
                print(f"⚠️  Viewer update error: {e}")

    def _update_viewer_safe(self):
        """Legacy method - now just sets update flag"""
        self.update_pending = True
    
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
        
        # Stop update timer
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
    
    def get_status(self):
        """Get current status"""
        status = "🔴 Stopped"
        if self.monitoring_active:
            status = "🟢 Active"
        
        print(f"📊 Status: {status}")
        print(f"📈 Frames loaded: {self.currentLastFrame}/{self.nFrames}")
        
        if self.currentLastFrame < self.nFrames:
            remaining = self.nFrames - self.currentLastFrame
            print(f"⏳ Remaining: {remaining} frames")
        else:
            print("✅ All frames loaded")
        
        return {
            'active': self.monitoring_active,
            'loaded': self.currentLastFrame,
            'total': self.nFrames,
            'remaining': self.nFrames - self.currentLastFrame
        }
    
    def run(self):
        """Run the live viewer (blocking)"""
        try:
            # Start monitoring
            self.start_live_monitoring(chunk_size=5, wait_time=0.5, fps=15)
            
            # Show initial status
            self.get_status()
            
            print("\n" + "="*50)
            print("🎮 Live Viewer Controls")
            print("="*50)
            print("Commands:")
            print("  's' + Enter: Show status")
            print("  'r' + Enter: Restart monitoring")
            print("  'q' + Enter: Quit")
            print("  Ctrl+C: Force quit")
            print("="*50)
            
            # Interactive control loop
            while True:
                try:
                    cmd = input().strip().lower()
                    if cmd == 's':
                        self.get_status()
                    elif cmd == 'r':
                        self.stop_monitoring()
                        time.sleep(1)
                        self.start_live_monitoring()
                    elif cmd == 'q':
                        break
                    elif cmd == '':
                        pass  # Ignore empty input
                    else:
                        print("❓ Unknown command. Use 's' for status, 'r' to restart, 'q' to quit.")
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n🛑 Interrupted by user")
                    break
            
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self.stop_monitoring()
            self.r.close()
            print("👋 Goodbye!")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Thorlabs Live Viewer")
    parser.add_argument("folder", nargs='?', default="../sampleImage",
                        help="Path to data folder (default: ../sampleImage)")
    parser.add_argument("--chunk-size", type=int, default=5,
                        help="Frames to load per chunk (default: 5)")
    parser.add_argument("--wait-time", type=float, default=0.5,
                        help="Wait time at live edge in seconds (default: 0.5)")
    parser.add_argument("--fps", type=float, default=15,
                        help="Expected acquisition FPS (default: 15)")
    
    args = parser.parse_args()
    
    # Check if folder exists
    if not os.path.exists(args.folder):
        print(f"❌ Error: Folder not found: {args.folder}")
        return 1
    
    try:
        # Create and run viewer
        viewer = ThorlabsLiveViewer(args.folder)
        viewer.run()
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
