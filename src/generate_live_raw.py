#!/usr/bin/env python3
"""
Live Raw File Generator for Testing
==================================

This script generates a raw file that simulates real-time microscopy acquisition.
It writes frames at 1 fps (or custom rate) with 512x512 uint16 data.

Perfect for testing the thorlabsLiveViewer live monitoring functionality!

Usage:
    python generate_live_raw.py [options]

Author: AI Assistant
Date: August 2025
"""

import os
import time
import numpy as np
import argparse
from datetime import datetime
from skimage.io import imsave
import threading

class LiveRawGenerator:
    def __init__(self, output_dir, width=512, height=512, total_frames=1000, fps=1.0):
        """
        Initialize the live raw file generator.
        
        Args:
            output_dir: Directory to save the files
            width: Frame width in pixels
            height: Frame height in pixels  
            total_frames: Total number of frames to pre-allocate
            fps: Frames per second to write
        """
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.total_frames = total_frames
        self.fps = fps
        self.frame_interval = 1.0 / fps
        
        # File paths
        self.raw_filename = "Image_001_001.raw"
        self.preview_filename = "ChanC_Preview.tif"
        self.raw_path = os.path.join(output_dir, self.raw_filename)
        self.preview_path = os.path.join(output_dir, self.preview_filename)
        
        # Frame properties
        self.frame_size = width * height * 2  # uint16 = 2 bytes
        self.total_file_size = self.frame_size * total_frames
        
        # Control flags
        self.stop_flag = threading.Event()
        self.is_writing = False
        self.frames_written = 0
        
        print(f"Initialized LiveRawGenerator:")
        print(f"  Frame size: {width}x{height} uint16")
        print(f"  Total frames: {total_frames}")
        print(f"  File size: {self.total_file_size / (1024*1024):.1f} MB")
        print(f"  Write rate: {fps} fps ({self.frame_interval:.1f}s per frame)")
    
    def create_preview_image(self):
        """Create a preview TIFF file (required by thorlabsFile)"""
        # Create a simple gradient pattern for preview
        preview = np.zeros((self.height, self.width), dtype=np.uint16)
        
        # Create a gradient with some structure
        y, x = np.meshgrid(np.arange(self.height), np.arange(self.width), indexing='ij')
        preview = (np.sin(x/50) * np.cos(y/50) * 32767 + 32767).astype(np.uint16)
        
        # Add some circular patterns
        center_y, center_x = self.height // 2, self.width // 2
        for i in range(3):
            cy = center_y + (i-1) * 100
            cx = center_x + (i-1) * 100
            dist = np.sqrt((y - cy)**2 + (x - cx)**2)
            mask = dist < 50
            preview[mask] = 65535 - preview[mask]
        
        imsave(self.preview_path, preview)
        print(f"✓ Created preview image: {self.preview_path}")
    
    def pre_allocate_file(self):
        """Pre-allocate the raw file with zeros (simulating unacquired frames)"""
        print(f"Pre-allocating {self.total_file_size / (1024*1024):.1f} MB file...")
        
        with open(self.raw_path, 'wb') as f:
            # Write in chunks to avoid memory issues
            chunk_size = 1024 * 1024  # 1MB chunks
            zero_chunk = np.zeros(chunk_size // 2, dtype=np.uint16).tobytes()
            
            bytes_written = 0
            while bytes_written < self.total_file_size:
                remaining = self.total_file_size - bytes_written
                if remaining < chunk_size:
                    # Last chunk
                    final_chunk = np.zeros(remaining // 2, dtype=np.uint16).tobytes()
                    f.write(final_chunk)
                    bytes_written += remaining
                else:
                    f.write(zero_chunk)
                    bytes_written += chunk_size
                
                # Progress indicator
                if bytes_written % (10 * 1024 * 1024) == 0:  # Every 10MB
                    progress = (bytes_written / self.total_file_size) * 100
                    print(f"  Progress: {progress:.1f}%")
        
        print(f"✓ Pre-allocated file: {self.raw_path}")
    
    def generate_frame(self, frame_number):
        """Generate a single frame with interesting patterns and frame number text"""
        # Create base noise
        frame = np.random.randint(1000, 5000, (self.height, self.width), dtype=np.uint16)
        
        # Add time-varying patterns
        t = frame_number * 0.1  # Time variable
        y, x = np.meshgrid(np.arange(self.height), np.arange(self.width), indexing='ij')
        
        # Moving wave pattern
        wave = np.sin(x/30 + t) * np.cos(y/25 + t*0.7) * 10000 + 10000
        frame = frame + wave.astype(np.uint16)
        
        # Moving bright spots
        for i in range(3):
            spot_x = int(256 + 150 * np.sin(t + i * 2))
            spot_y = int(256 + 150 * np.cos(t * 0.8 + i * 2))
            
            # Create Gaussian spot
            dist = np.sqrt((x - spot_x)**2 + (y - spot_y)**2)
            spot = np.exp(-dist**2 / (20**2)) * 20000
            frame = frame + spot.astype(np.uint16)
        
        # Add frame number text overlay
        self._add_frame_number_text(frame, frame_number)
        
        # Ensure we don't overflow
        frame = np.clip(frame, 0, 65535)
        
        return frame
    
    def _add_frame_number_text(self, frame, frame_number):
        """Add frame number text overlay to the frame"""
        # Create simple bitmap font for digits (8x12 pixels per character)
        # Define digit patterns (simplified 8x12 bitmap for digits 0-9)
        digit_patterns = {
            '0': [
                "  ████  ",
                " ██  ██ ",
                "██    ██",
                "██    ██",
                "██    ██",
                "██    ██",
                "██    ██",
                "██    ██",
                "██    ██",
                " ██  ██ ",
                "  ████  ",
                "        "
            ],
            '1': [
                "   ██   ",
                "  ███   ",
                " ████   ",
                "   ██   ",
                "   ██   ",
                "   ██   ",
                "   ██   ",
                "   ██   ",
                "   ██   ",
                "   ██   ",
                " ██████ ",
                "        "
            ],
            '2': [
                "  ████  ",
                " ██  ██ ",
                "██    ██",
                "      ██",
                "     ██ ",
                "    ██  ",
                "   ██   ",
                "  ██    ",
                " ██     ",
                "██      ",
                "████████",
                "        "
            ],
            '3': [
                "  ████  ",
                " ██  ██ ",
                "██    ██",
                "      ██",
                "   ████ ",
                "      ██",
                "      ██",
                "██    ██",
                "██    ██",
                " ██  ██ ",
                "  ████  ",
                "        "
            ],
            '4': [
                "     ██ ",
                "    ███ ",
                "   ████ ",
                "  ██ ██ ",
                " ██  ██ ",
                "██   ██ ",
                "████████",
                "     ██ ",
                "     ██ ",
                "     ██ ",
                "     ██ ",
                "        "
            ],
            '5': [
                "████████",
                "██      ",
                "██      ",
                "██      ",
                "██████  ",
                " ██  ██ ",
                "      ██",
                "      ██",
                "██    ██",
                " ██  ██ ",
                "  ████  ",
                "        "
            ],
            '6': [
                "  ████  ",
                " ██  ██ ",
                "██    ██",
                "██      ",
                "██████  ",
                "███  ██ ",
                "██    ██",
                "██    ██",
                "██    ██",
                " ██  ██ ",
                "  ████  ",
                "        "
            ],
            '7': [
                "████████",
                "      ██",
                "     ██ ",
                "    ██  ",
                "   ██   ",
                "  ██    ",
                " ██     ",
                "██      ",
                "██      ",
                "██      ",
                "██      ",
                "        "
            ],
            '8': [
                "  ████  ",
                " ██  ██ ",
                "██    ██",
                "██    ██",
                " ██  ██ ",
                "  ████  ",
                " ██  ██ ",
                "██    ██",
                "██    ██",
                " ██  ██ ",
                "  ████  ",
                "        "
            ],
            '9': [
                "  ████  ",
                " ██  ██ ",
                "██    ██",
                "██    ██",
                "██    ██",
                " ██  ███",
                "  ██████",
                "      ██",
                "██    ██",
                " ██  ██ ",
                "  ████  ",
                "        "
            ]
        }
        
        # Convert frame number to string
        frame_text = f"Frame {frame_number}"
        
        # Position for text (top-left corner with some padding)
        start_y = 10
        start_x = 10
        
        # Draw each character
        char_width = 8
        char_height = 12
        char_spacing = 2
        
        current_x = start_x
        
        for char in frame_text:
            if char == ' ':
                current_x += char_width + char_spacing
                continue
            elif char in digit_patterns:
                pattern = digit_patterns[char]
            elif char.upper() in ['F', 'R', 'A', 'M', 'E']:
                # Simple patterns for letters F, R, A, M, E
                if char.upper() == 'F':
                    pattern = [
                        "████████",
                        "██      ",
                        "██      ",
                        "██      ",
                        "██████  ",
                        "██      ",
                        "██      ",
                        "██      ",
                        "██      ",
                        "██      ",
                        "██      ",
                        "        "
                    ]
                elif char.upper() == 'R':
                    pattern = [
                        "██████  ",
                        "██   ██ ",
                        "██    ██",
                        "██    ██",
                        "██   ██ ",
                        "██████  ",
                        "██  ██  ",
                        "██   ██ ",
                        "██    ██",
                        "██    ██",
                        "██     █",
                        "        "
                    ]
                elif char.upper() == 'A':
                    pattern = [
                        "   ██   ",
                        "  ████  ",
                        " ██  ██ ",
                        "██    ██",
                        "██    ██",
                        "██    ██",
                        "████████",
                        "██    ██",
                        "██    ██",
                        "██    ██",
                        "██    ██",
                        "        "
                    ]
                elif char.upper() == 'M':
                    pattern = [
                        "██    ██",
                        "███  ███",
                        "████████",
                        "██ ██ ██",
                        "██ ██ ██",
                        "██    ██",
                        "██    ██",
                        "██    ██",
                        "██    ██",
                        "██    ██",
                        "██    ██",
                        "        "
                    ]
                elif char.upper() == 'E':
                    pattern = [
                        "████████",
                        "██      ",
                        "██      ",
                        "██      ",
                        "██████  ",
                        "██      ",
                        "██      ",
                        "██      ",
                        "██      ",
                        "██      ",
                        "████████",
                        "        "
                    ]
                else:
                    # Default pattern for unknown characters
                    pattern = [" " * 8] * 12
            else:
                # Skip unknown characters
                current_x += char_width + char_spacing
                continue
            
            # Draw the character pattern
            for row, line in enumerate(pattern):
                y = start_y + row
                if y >= self.height:
                    break
                    
                for col, pixel in enumerate(line):
                    x = current_x + col
                    if x >= self.width:
                        break
                        
                    if pixel == '█':  # Filled pixel
                        if 0 <= y < self.height and 0 <= x < self.width:
                            frame[y, x] = 65535  # Bright white text
            
            current_x += char_width + char_spacing
    
    def start_writing(self):
        """Start writing frames to the file at the specified fps"""
        if self.is_writing:
            print("Already writing!")
            return
        
        print(f"\n🎬 Starting live writing at {self.fps} fps...")
        print("Press Ctrl+C to stop")
        
        self.is_writing = True
        self.frames_written = 0
        
        def write_thread():
            with open(self.raw_path, 'r+b') as f:
                start_time = time.time()
                
                while not self.stop_flag.is_set() and self.frames_written < self.total_frames:
                    # Generate frame
                    frame = self.generate_frame(self.frames_written)
                    
                    # Write to correct position in file
                    offset = self.frames_written * self.frame_size
                    f.seek(offset)
                    f.write(frame.tobytes())
                    f.flush()  # Ensure data is written to disk
                    
                    self.frames_written += 1
                    elapsed = time.time() - start_time
                    
                    # Progress report
                    if self.frames_written % 10 == 0 or self.frames_written <= 5:
                        print(f"📝 Frame {self.frames_written}/{self.total_frames} written "
                              f"(elapsed: {elapsed:.1f}s, avg fps: {self.frames_written/elapsed:.2f})")
                    
                    # Wait for next frame time
                    target_time = start_time + self.frames_written * self.frame_interval
                    sleep_time = target_time - time.time()
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            
            self.is_writing = False
            if self.frames_written >= self.total_frames:
                print(f"✅ Completed! Wrote all {self.total_frames} frames")
            else:
                print(f"⏹️  Stopped at frame {self.frames_written}")
        
        # Start writing thread
        self.write_thread = threading.Thread(target=write_thread, daemon=True)
        self.write_thread.start()
    
    def stop_writing(self):
        """Stop the writing process"""
        if self.is_writing:
            self.stop_flag.set()
            print("🛑 Stopping live writing...")
            if hasattr(self, 'write_thread'):
                self.write_thread.join(timeout=2)
        else:
            print("Not currently writing")
    
    def get_status(self):
        """Get current status"""
        if self.is_writing:
            print(f"📊 Status: Writing frame {self.frames_written}/{self.total_frames}")
        else:
            print(f"📊 Status: Stopped at frame {self.frames_written}/{self.total_frames}")
        return self.frames_written


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Generate live raw microscopy file")
    parser.add_argument("--output-dir", "-o", default="../sampleImage", 
                        help="Output directory (default: ../sampleImage)")
    parser.add_argument("--width", "-w", type=int, default=512, 
                        help="Frame width (default: 512)")
    parser.add_argument("--height", type=int, default=512, 
                        help="Frame height (default: 512)")
    parser.add_argument("--frames", "-f", type=int, default=1000, 
                        help="Total frames to pre-allocate (default: 1000)")
    parser.add_argument("--fps", type=float, default=1.0, 
                        help="Frames per second (default: 1.0)")
    parser.add_argument("--no-preview", action="store_true", 
                        help="Skip creating preview image")
    parser.add_argument("--no-prealloc", action="store_true", 
                        help="Skip pre-allocation (for testing)")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create generator
    generator = LiveRawGenerator(
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        total_frames=args.frames,
        fps=args.fps
    )
    
    try:
        # Create preview image
        if not args.no_preview:
            generator.create_preview_image()
        
        # Pre-allocate file
        if not args.no_prealloc:
            generator.pre_allocate_file()
        
        # Start writing
        generator.start_writing()
        
        # Interactive control
        print("\n" + "="*50)
        print("Live Raw Generator Control")
        print("="*50)
        print("Commands:")
        print("  's' + Enter: Show status")
        print("  'q' + Enter: Quit")
        print("  Ctrl+C: Force quit")
        print("="*50)
        
        while generator.is_writing:
            try:
                cmd = input().strip().lower()
                if cmd == 's':
                    generator.get_status()
                elif cmd == 'q':
                    break
                elif cmd == '':
                    pass  # Ignore empty input
                else:
                    print("Unknown command. Use 's' for status, 'q' to quit.")
            except EOFError:
                break
        
        generator.stop_writing()
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        generator.stop_writing()
    except Exception as e:
        print(f"❌ Error: {e}")
        generator.stop_writing()
    finally:
        print("👋 Goodbye!")


if __name__ == "__main__":
    main()
