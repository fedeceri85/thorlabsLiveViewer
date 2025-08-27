#!/usr/bin/env python3
"""
Thorlabs Live Viewer GUI
=========================

Qt GUI application for controlling the Thorlabs Live Viewer with
easy parameter input and folder selection.

Features:
- Folder selection dialog
- Parameter adjustment (chunk size, wait time, FPS)
- Start/Stop monitoring controls
- Status display
- Automatic reset when new folder is selected

Usage:
    python thorlabs_gui_app.py

Author: AI Assistant
Date: August 2025
"""

import os
import sys
sys.path.append('./src')
import threading
import time
from pathlib import Path

from qtpy.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                           QSpinBox, QDoubleSpinBox, QFileDialog, QTextEdit,
                           QGroupBox, QGridLayout, QMessageBox, QProgressBar)
from qtpy.QtCore import QTimer, QObject, Signal, Qt
from qtpy.QtGui import QFont, QIcon

# Import the live viewer
from thorlabs_live_viewer_simple import ThorlabsLiveViewerSimple


class StatusUpdater(QObject):
    """Qt object for thread-safe status updates"""
    status_update = Signal(str)
    progress_update = Signal(int, int)  # current, total


class ThorlabsGUI(QMainWindow):
    """Main GUI application for Thorlabs Live Viewer"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize variables
        self.viewer = None
        self.current_folder = None
        
        # Status updater
        self.status_updater = StatusUpdater()
        self.status_updater.status_update.connect(self.update_status_display)
        self.status_updater.progress_update.connect(self.update_progress)
        
        # Setup UI
        self.init_ui()
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(1000)  # Update every second
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Thorlabs Live Viewer Control Panel")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🔬 Thorlabs Live Viewer Control Panel")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Folder selection group
        folder_group = QGroupBox("📂 Data Folder")
        folder_layout = QHBoxLayout(folder_group)
        
        self.folder_line_edit = QLineEdit()
        self.folder_line_edit.setPlaceholderText("Select a folder containing raw data...")
        self.folder_line_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_line_edit)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_button)
        
        layout.addWidget(folder_group)
        
        # Parameters group
        params_group = QGroupBox("⚙️ Monitoring Parameters")
        params_layout = QGridLayout(params_group)
        
        # Chunk size
        params_layout.addWidget(QLabel("Chunk Size (frames):"), 0, 0)
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 2000)
        self.chunk_size_spin.setValue(100)
        self.chunk_size_spin.setToolTip("Number of frames to load per chunk")
        params_layout.addWidget(self.chunk_size_spin, 0, 1)
        
        # Wait time
        params_layout.addWidget(QLabel("Wait Time (seconds):"), 1, 0)
        self.wait_time_spin = QDoubleSpinBox()
        self.wait_time_spin.setRange(5, 120)
        self.wait_time_spin.setValue(5)
        self.wait_time_spin.setSingleStep(5)
        self.wait_time_spin.setDecimals(1)
        self.wait_time_spin.setToolTip("Wait time at live edge")
        params_layout.addWidget(self.wait_time_spin, 1, 1)
        
        # # Expected FPS
        # params_layout.addWidget(QLabel("Expected FPS:"), 2, 0)
        # self.fps_spin = QDoubleSpinBox()
        # self.fps_spin.setRange(1.0, 60.0)
        # self.fps_spin.setValue(15.0)
        # self.fps_spin.setSingleStep(1.0)
        # self.fps_spin.setDecimals(1)
        # self.fps_spin.setToolTip("Expected frame rate for adaptive timing")
        # params_layout.addWidget(self.fps_spin, 2, 1)
        
        layout.addWidget(params_group)
        
        # Control buttons
        control_group = QGroupBox("🎮 Controls")
        control_layout = QHBoxLayout(control_group)
        
        self.start_button = QPushButton("🚀 Start Monitoring")
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("🛑 Stop Monitoring")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.restart_button = QPushButton("🔄 Restart")
        self.restart_button.clicked.connect(self.restart_monitoring)
        self.restart_button.setEnabled(False)
        control_layout.addWidget(self.restart_button)
        
        layout.addWidget(control_group)
        
        # Progress group
        progress_group = QGroupBox("📊 Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready to start...")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        # Status display
        status_group = QGroupBox("📋 Status Log")
        status_layout = QVBoxLayout(status_group)
        
        self.status_display = QTextEdit()
        self.status_display.setMaximumHeight(200)
        self.status_display.setFont(QFont("Courier", 10))
        self.status_display.append("🔬 Thorlabs Live Viewer GUI Ready")
        self.status_display.append("👆 Select a data folder to begin")
        status_layout.addWidget(self.status_display)
        
        clear_button = QPushButton("🗑️ Clear Log")
        clear_button.clicked.connect(self.status_display.clear)
        status_layout.addWidget(clear_button)
        
        layout.addWidget(status_group)
    
    def browse_folder(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Data Folder",
            str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.set_folder(folder)
    
    def set_folder(self, folder):
        """Set the current folder and validate it"""
        self.current_folder = folder
        self.folder_line_edit.setText(folder)
        
        # Reset any existing viewer
        if self.viewer:
            self.stop_monitoring()
            self.viewer = None
        
        # Validate folder
        raw_file = os.path.join(folder, "Image_001_001.raw")
        preview_file = os.path.join(folder, "ChanC_Preview.tif")
        
        if os.path.exists(raw_file) and os.path.exists(preview_file):
            self.log_status(f"✅ Valid folder selected: {os.path.basename(folder)}")
            self.log_status(f"📁 Found: {os.path.basename(raw_file)}")
            self.log_status(f"🖼️  Found: {os.path.basename(preview_file)}")
            self.start_button.setEnabled(True)
        else:
            self.log_status(f"❌ Invalid folder: Missing required files")
            if not os.path.exists(raw_file):
                self.log_status(f"❌ Missing: Image_001_001.raw")
            if not os.path.exists(preview_file):
                self.log_status(f"❌ Missing: ChanC_Preview.tif")
            self.start_button.setEnabled(False)
            
            QMessageBox.warning(
                self, 
                "Invalid Folder",
                "The selected folder does not contain the required files:\n"
                "• Image_001_001.raw\n"
                "• ChanC_Preview.tif"
            )
    
    def start_monitoring(self):
        """Start live monitoring"""
        if not self.current_folder:
            return
        
        try:
            # Create viewer
            self.log_status("🔬 Initializing viewer...")
            self.viewer = ThorlabsLiveViewerSimple(self.current_folder)
            
            # Start monitoring with current parameters
            chunk_size = self.chunk_size_spin.value()
            wait_time = self.wait_time_spin.value()
           # fps = self.fps_spin.value()
            
            self.log_status(f"🚀 Starting monitoring (chunk={chunk_size}, wait={wait_time}s")
            self.viewer.start_live_monitoring(chunk_size, wait_time)

            # Update UI state
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.restart_button.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(self.viewer.nFrames)
            
            self.log_status("✅ Monitoring started successfully!")
            
        except Exception as e:
            self.log_status(f"❌ Error starting monitoring: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start monitoring:\n{e}")
    
    def stop_monitoring(self):
        """Stop live monitoring"""
        if self.viewer:
            self.log_status("🛑 Stopping monitoring...")
            self.viewer.stop_monitoring()
            
            # Update UI state
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.restart_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            
            self.log_status("✅ Monitoring stopped")
    
    def restart_monitoring(self):
        """Restart monitoring with current parameters"""
        if self.viewer:
            self.log_status("🔄 Restarting monitoring...")
            
            chunk_size = self.chunk_size_spin.value()
            wait_time = self.wait_time_spin.value()
        #    fps = self.fps_spin.value()
            
            self.viewer.restart_monitoring(chunk_size, wait_time)
            self.log_status(f"🔄 Restarted with chunk={chunk_size}, wait={wait_time}sß")
    
    def refresh_status(self):
        """Refresh status display (called by timer)"""
        if self.viewer and self.viewer.monitoring_active:
            try:
                status = self.viewer.get_status()
                
                # Update progress
                current = status['frames_loaded']
                total = status['total_frames']
                remaining = status['remaining']
                
                self.progress_bar.setValue(current)
                self.progress_label.setText(
                    f"📈 Frames: {current}/{total} | ⏳ Remaining: {remaining}"
                )
                
                # Emit signal for thread-safe update
                self.status_updater.progress_update.emit(current, total)
                
            except Exception as e:
                pass  # Ignore errors during status refresh
    
    def update_status_display(self, message):
        """Update status display (thread-safe)"""
        self.status_display.append(message)
        # Auto-scroll to bottom
        cursor = self.status_display.textCursor()
        cursor.movePosition(cursor.End)
        self.status_display.setTextCursor(cursor)
    
    def update_progress(self, current, total):
        """Update progress (thread-safe)"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(current)
    
    def log_status(self, message):
        """Add message to status log"""
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        self.status_display.append(full_message)
        
        # Auto-scroll to bottom
        cursor = self.status_display.textCursor()
        cursor.movePosition(cursor.End)
        self.status_display.setTextCursor(cursor)
    
    def closeEvent(self, event):
        """Handle application closing"""
        if self.viewer:
            self.stop_monitoring()
        
        # Stop timers
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        event.accept()


def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Thorlabs Live Viewer")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Research Lab")
    
    # Create and show main window
    window = ThorlabsGUI()
    window.show()
    
    # Check if folder was provided as command line argument
    if len(sys.argv) > 1:
        folder = sys.argv[1]
        if os.path.exists(folder):
            window.set_folder(folder)
    
    # Run application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
