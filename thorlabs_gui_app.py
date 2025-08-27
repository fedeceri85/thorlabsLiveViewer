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
                           QGroupBox, QGridLayout, QMessageBox, QProgressBar,
                           QCheckBox, QTabWidget)
from qtpy.QtCore import QTimer, QObject, Signal, Qt
from qtpy.QtGui import QFont, QIcon, QPalette

import pyqtgraph as pg
import numpy as np

# Import the live viewer
from thorlabs_live_viewer_simple import ThorlabsLiveViewerSimple


class StatusUpdater(QObject):
    """Qt object for thread-safe status updates"""
    status_update = Signal(str)
    progress_update = Signal(int, int)  # current, total
    roi_update = Signal(np.ndarray)  # ROI data for plotting


class ThorlabsGUI(QMainWindow):
    """Main GUI application for Thorlabs Live Viewer"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize variables
        self.viewer = None
        self.current_folder = None
        
        # ROI monitoring variables
        self.roi_data = {}  # Dictionary to store data for multiple ROIs
        self.roi_enabled = False
        self.roi_window = None
        self.napari_shapes_layer = None
        
        # ROI color management
        self.roi_colors = ['#00ff00', '#ff0000', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', 
                          '#ffa500', '#ff69b4', '#32cd32', '#ba55d3', '#20b2aa', '#dda0dd']
        self.color_index = 0  # Track next color to assign
        self.roi_color_map = {}  # Map ROI names to colors
        
        # Status updater
        self.status_updater = StatusUpdater()
        self.status_updater.status_update.connect(self.update_status_display)
        self.status_updater.progress_update.connect(self.update_progress)
        self.status_updater.roi_update.connect(self.update_roi_plot)
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Setup UI
        self.init_ui()
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(1000)  # Update every second
    
    def apply_dark_theme(self):
        """Apply dark theme to prevent stray light affecting PMTs"""
        dark_stylesheet = """
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            border: none;
        }
        
        QGroupBox {
            background-color: #2d2d2d;
            border: 2px solid #555555;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 10px;
            color: #ffffff;
            font-weight: bold;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff;
        }
        
        QPushButton {
            background-color: #404040;
            border: 2px solid #606060;
            border-radius: 6px;
            padding: 8px;
            color: #ffffff;
            font-weight: bold;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #505050;
            border-color: #707070;
        }
        
        QPushButton:pressed {
            background-color: #303030;
        }
        
        QPushButton:disabled {
            background-color: #2a2a2a;
            border-color: #3a3a3a;
            color: #666666;
        }
        
        QLineEdit {
            background-color: #2d2d2d;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 5px;
            color: #ffffff;
        }
        
        QLineEdit:focus {
            border-color: #0078d4;
        }
        
        QSpinBox, QDoubleSpinBox {
            background-color: #2d2d2d;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 5px;
            color: #ffffff;
        }
        
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #0078d4;
        }
        
        QTextEdit {
            background-color: #1a1a1a;
            border: 2px solid #555555;
            border-radius: 4px;
            color: #ffffff;
            font-family: 'Courier New', monospace;
        }
        
        QProgressBar {
            background-color: #2d2d2d;
            border: 2px solid #555555;
            border-radius: 4px;
            text-align: center;
            color: #ffffff;
        }
        
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 2px;
        }
        
        QLabel {
            color: #ffffff;
            background-color: transparent;
        }
        
        QMessageBox {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        QMessageBox QLabel {
            color: #ffffff;
        }
        
        QMessageBox QPushButton {
            min-width: 80px;
        }
        
        QFileDialog {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        QTabWidget::pane {
            border: 2px solid #555555;
            background-color: #2d2d2d;
        }
        
        QTabBar::tab {
            background-color: #404040;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        
        QTabBar::tab:hover {
            background-color: #505050;
        }
        
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        
        QCheckBox::indicator:unchecked {
            background-color: #2d2d2d;
            border: 2px solid #555555;
            border-radius: 3px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border: 2px solid #0078d4;
            border-radius: 3px;
        }
        """
        
        self.setStyleSheet(dark_stylesheet)
        
        # Configure PyQtGraph for dark theme
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#ffffff')
        pg.setConfigOption('antialias', True)
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Thorlabs Live Viewer Control Panel - Dark Mode")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🔬 Thorlabs Live Viewer Control Panel (Dark Mode)")
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
        
        # Gaussian filter toggle
        self.gaussian_checkbox = QCheckBox("🌟 Apply Gaussian Filter")
        self.gaussian_checkbox.setChecked(True)  # Default to enabled
        self.gaussian_checkbox.setToolTip("Apply Gaussian smoothing filter to reduce noise")
        params_layout.addWidget(self.gaussian_checkbox, 2, 0, 1, 2)
        
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
        
        # ROI Monitoring group
        roi_group = QGroupBox("📊 ROI Monitoring")
        roi_layout = QGridLayout(roi_group)
        
        # Enable ROI monitoring checkbox
        self.roi_enable_checkbox = QCheckBox("Enable ROI Monitoring")
        self.roi_enable_checkbox.toggled.connect(self.toggle_roi_monitoring)
        roi_layout.addWidget(self.roi_enable_checkbox, 0, 0, 1, 2)
        
        # Info label
        roi_info = QLabel("💡 Draw shapes in Napari to create ROIs")
        roi_info.setStyleSheet("color: #aaaaaa; font-style: italic;")
        roi_layout.addWidget(roi_info, 1, 0, 1, 2)
        
        # Show ROI plot button
        self.show_roi_button = QPushButton("📈 Show ROI Plot")
        self.show_roi_button.clicked.connect(self.show_roi_window)
        self.show_roi_button.setEnabled(False)
        roi_layout.addWidget(self.show_roi_button, 2, 0, 1, 2)
        
        # Manual ROI update button
        self.update_roi_button = QPushButton("🔄 Update ROI Data")
        self.update_roi_button.clicked.connect(self.manual_roi_update)
        self.update_roi_button.setEnabled(False)
        roi_layout.addWidget(self.update_roi_button, 3, 0, 1, 2)
        
        layout.addWidget(roi_group)
        
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
            self.viewer.close()  # Properly close the viewer
            self.viewer = None
            self.napari_shapes_layer = None  # Reset ROI connection
        
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
            # Create viewer only if it doesn't exist
            if self.viewer is None:
                self.log_status("🔬 Initializing viewer...")
                self.viewer = ThorlabsLiveViewerSimple(self.current_folder)
            else:
                self.log_status("🔬 Using existing viewer...")
                # Reset ROI connection since we're starting fresh
                self.napari_shapes_layer = None
            
            # Start monitoring with current parameters
            chunk_size = self.chunk_size_spin.value()
            wait_time = self.wait_time_spin.value()
            use_gaussian = self.gaussian_checkbox.isChecked()
           # fps = self.fps_spin.value()
            
            self.log_status(f"🚀 Starting monitoring (chunk={chunk_size}, wait={wait_time}s, gaussian={use_gaussian})")
            self.viewer.start_live_monitoring(chunk_size, wait_time, use_gaussian_filter=use_gaussian)

            # Connect to Napari shapes layer for ROI monitoring
            self.connect_to_napari_shapes()

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
            
            # Reset ROI connection since data arrays will be reset
            self.napari_shapes_layer = None
            
            chunk_size = self.chunk_size_spin.value()
            wait_time = self.wait_time_spin.value()
            use_gaussian = self.gaussian_checkbox.isChecked()
        #    fps = self.fps_spin.value()
            
            self.viewer.restart_monitoring(chunk_size, wait_time, use_gaussian_filter=use_gaussian)
            
            # Reconnect to Napari shapes layer after restart
            self.connect_to_napari_shapes()
            
            self.log_status(f"🔄 Restarted with chunk={chunk_size}, wait={wait_time}s, gaussian={use_gaussian}")
    
    def toggle_roi_monitoring(self, enabled):
        """Toggle ROI monitoring on/off"""
        self.roi_enabled = enabled
        self.show_roi_button.setEnabled(enabled)
        self.update_roi_button.setEnabled(enabled)
        
        if enabled:
            self.log_status("📊 ROI monitoring enabled - draw shapes in Napari")
            # Clear previous data and color assignments
            self.roi_data = {}
            self.roi_color_map = {}
            self.color_index = 0
        else:
            self.log_status("📊 ROI monitoring disabled")
            if self.roi_window:
                self.roi_window.close()
                self.roi_window = None
    
    def connect_to_napari_shapes(self):
        """Connect to Napari's shapes layer for ROI monitoring"""
        if self.viewer and hasattr(self.viewer, 'app'):
            try:
                print(f"Available layers in Napari: {len(self.viewer.app.layers)}")
                
                # List all layers for debugging
                for i, layer in enumerate(self.viewer.app.layers):
                    print(f"Layer {i}: name='{layer.name}', type={type(layer)}")
                    print(f"  - Has data: {hasattr(layer, 'data')}")
                    print(f"  - Has shape_type: {hasattr(layer, 'shape_type')}")
                    if hasattr(layer, 'shape_type'):
                        print(f"  - Shape type: {layer.shape_type}")
                
                # Find the shapes layer by name (should be 'Annotations')
                for layer in self.viewer.app.layers:
                    if layer.name == 'Annotations':
                        self.napari_shapes_layer = layer
                        print(f'✅ Found Napari shapes layer by name: {layer}')
                        # Connect to shape events
                        layer.events.data.connect(self.on_shapes_changed)
                        self.log_status("🔗 Connected to Napari Annotations layer")
                        return
                
                # If not found by name, try to find any shapes layer by type
                for layer in self.viewer.app.layers:
                    layer_type = str(type(layer))
                    print(f"Checking layer type: {layer_type}")
                    if 'shapes' in layer_type.lower() or 'shape' in layer_type.lower():
                        self.napari_shapes_layer = layer
                        print(f'✅ Found Napari shapes layer by type: {layer}')
                        # Connect to shape events
                        layer.events.data.connect(self.on_shapes_changed)
                        self.log_status(f"🔗 Connected to Napari layer: {layer.name}")
                        return
                
                # Last attempt: check for layers with shape_type attribute
                for layer in self.viewer.app.layers:
                    if hasattr(layer, 'shape_type'):
                        self.napari_shapes_layer = layer
                        print(f'✅ Found layer with shape_type: {layer}')
                        # Connect to shape events
                        layer.events.data.connect(self.on_shapes_changed)
                        self.log_status(f"🔗 Connected to Napari layer: {layer.name}")
                        return
                
                self.log_status("⚠️  No shapes layer found in Napari - will retry later")
                    
            except Exception as e:
                self.log_status(f"⚠️  Error connecting to Napari shapes: {e}")
                import traceback
                traceback.print_exc()
    
    def retry_napari_connection(self):
        """Retry connecting to Napari shapes layer"""
        if self.napari_shapes_layer is None and self.viewer:
            print("Retrying Napari shapes connection...")
            self.connect_to_napari_shapes()
    
    def on_shapes_changed(self, event):
        """Called when shapes are modified in Napari"""
        if self.roi_enabled:
            self.log_status("🔄 ROI shapes updated - press 'Update ROI Data' to refresh")
            # Update shape colors dynamically when shapes change
            self.update_shape_colors()
            # Don't automatically clear data - let user control updates manually
    
    def update_shape_colors(self):
        """Update Napari shape colors to use our color palette"""
        if not self.napari_shapes_layer:
            return
        
        try:
            shapes_data = self.napari_shapes_layer.data
            n_shapes = len(shapes_data)
            
            if n_shapes > 0:
                # Create color array for all shapes
                edge_colors = []
                
                for i in range(n_shapes):
                    roi_name = f"ROI_{i}"
                    
                    # Assign new color if this ROI doesn't have one
                    if roi_name not in self.roi_color_map:
                        color = self.roi_colors[self.color_index % len(self.roi_colors)]
                        self.roi_color_map[roi_name] = color
                        self.color_index += 1
                    
                    # Convert hex color to RGB array
                    hex_color = self.roi_color_map[roi_name]
                    rgb = [int(hex_color[1:3], 16)/255, int(hex_color[3:5], 16)/255, int(hex_color[5:7], 16)/255, 1.0]
                    edge_colors.append(rgb)
                
                # Update the layer colors
                self.napari_shapes_layer.edge_color = edge_colors
                print(f"🎨 Updated colors for {n_shapes} ROIs")
                
        except Exception as e:
            print(f"Error updating shape colors: {e}")
    
    def get_roi_color(self, roi_name):
        """Get the color for a specific ROI"""
        if roi_name not in self.roi_color_map:
            color = self.roi_colors[self.color_index % len(self.roi_colors)]
            self.roi_color_map[roi_name] = color
            self.color_index += 1
        return self.roi_color_map[roi_name]
    
    def manual_roi_update(self):
        """Manually update ROI data when button is pressed"""
        if not self.roi_enabled:
            return
        
        if self.viewer and hasattr(self.viewer, 'array') and self.viewer.array.size > 0:
            self.log_status("🔄 Manually updating ROI data...")
            # Clear existing ROI data and curves for fresh update
            self.roi_data = {}
            
            # Clear existing plot curves
            if hasattr(self, 'roi_curves'):
                for roi_name, curve in self.roi_curves.items():
                    self.roi_plot_widget.removeItem(curve)
                self.roi_curves = {}
            
            # Update shape colors before extracting data
            self.update_shape_colors()
            
            # Update with current data
            self.update_roi_plot(self.viewer.array)
            self.log_status("✅ ROI data updated manually")
        else:
            self.log_status("⚠️  No data available for ROI update")
    
    def show_roi_window(self):
        """Show/create ROI plotting window"""
        if self.roi_window is None:
            self.create_roi_window()
        else:
            self.roi_window.show()
            self.roi_window.raise_()
            self.roi_window.activateWindow()
    
    def create_roi_window(self):
        """Create the ROI plotting window"""
        self.roi_window = QWidget()
        self.roi_window.setWindowTitle("Live ROI Monitor (Napari Shapes)")
        self.roi_window.setGeometry(850, 100, 700, 500)
        
        # Apply dark theme to ROI window
        self.roi_window.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(self.roi_window)
        
        # Create plot widget
        self.roi_plot_widget = pg.PlotWidget(title="ROI Intensities Over Time")
        self.roi_plot_widget.setLabel('left', 'Mean Intensity', units='AU')
        self.roi_plot_widget.setLabel('bottom', 'Frame Number')
        self.roi_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.roi_plot_widget.addLegend()
        
        # Dictionary to store plot curves for different ROIs
        self.roi_curves = {}
        
        layout.addWidget(self.roi_plot_widget)
        
        # ROI info label
        self.roi_info_label = QLabel("ROI Monitor: Draw shapes in Napari to create ROIs")
        self.roi_info_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(self.roi_info_label)
        
        self.roi_window.show()
        self.log_status("📈 ROI plot window opened")
    
    def extract_napari_roi_data(self, image_data):
        """Extract ROI data from Napari shapes"""
        if not self.roi_enabled or image_data is None or image_data.size == 0:
            return {}
        
        if self.napari_shapes_layer is None:
            return {}
        
        try:
            # Get current frame (last frame in the stack)
            if len(image_data.shape) == 3:
                current_frame = image_data[-1]
            else:
                current_frame = image_data
            
            roi_values = {}
            
            # Get shapes from Napari layer
            shapes_data = self.napari_shapes_layer.data
            
            for i, shape in enumerate(shapes_data):
                try:
                    roi_name = f"ROI_{i}"
                    
                    # If this is a new ROI, calculate historical data
                    if roi_name not in self.roi_data:
                        self.roi_data[roi_name] = []
                        # Extract ROI data from all previous frames
                        historical_data = self.extract_roi_from_all_frames(shape, image_data)
                        self.roi_data[roi_name] = historical_data
                    
                    # Create a mask for this shape
                    if len(shape) >= 3:  # Minimum points for a meaningful shape
                        # Convert shape coordinates to integer indices
                        shape_coords = np.array(shape, dtype=int)
                        
                        # Create mask using polygon
                        from skimage.draw import polygon
                        
                        # Ensure coordinates are within image bounds
                        shape_coords[:, 0] = np.clip(shape_coords[:, 0], 0, current_frame.shape[0]-1)
                        shape_coords[:, 1] = np.clip(shape_coords[:, 1], 0, current_frame.shape[1]-1)
                        
                        # Create mask
                        mask = np.zeros(current_frame.shape, dtype=bool)
                        rr, cc = polygon(shape_coords[:, 0], shape_coords[:, 1], current_frame.shape)
                        mask[rr, cc] = True
                        
                        # Extract ROI values
                        roi_pixels = current_frame[mask]
                        if len(roi_pixels) > 0:
                            roi_mean = np.mean(roi_pixels)
                            roi_values[roi_name] = roi_mean
                
                except Exception as e:
                    print(f"Error processing shape {i}: {e}")
                    continue
            
            return roi_values
            
        except Exception as e:
            print(f"ROI extraction error: {e}")
            return {}
    
    def extract_roi_from_all_frames(self, shape, image_data):
        """Extract ROI data from all frames in the image stack for a new ROI"""
        historical_data = []
        
        try:
            # Create a mask for this shape
            if len(shape) >= 3:  # Minimum points for a meaningful shape
                # Convert shape coordinates to integer indices
                shape_coords = np.array(shape, dtype=int)
                
                from skimage.draw import polygon
                
                # Process all frames in the stack (vectorized)
                if len(image_data.shape) == 3:
                    # Ensure coordinates are within image bounds (use first frame for bounds)
                    first_frame = image_data[0]
                    clipped_coords = shape_coords.copy()
                    clipped_coords[:, 0] = np.clip(clipped_coords[:, 0], 0, first_frame.shape[0]-1)
                    clipped_coords[:, 1] = np.clip(clipped_coords[:, 1], 0, first_frame.shape[1]-1)
                    
                    # Create mask once (same for all frames)
                    mask = np.zeros(first_frame.shape, dtype=bool)
                    rr, cc = polygon(clipped_coords[:, 0], clipped_coords[:, 1], first_frame.shape)
                    mask[rr, cc] = True
                    
                    # Vectorized ROI extraction for all frames at once
                    # Extract ROI pixels from all frames simultaneously
                    roi_pixels_all_frames = image_data[:, mask]  # Shape: (n_frames, n_roi_pixels)
                    
                    # Calculate mean for each frame (vectorized)
                    roi_means = np.mean(roi_pixels_all_frames, axis=1)
                    historical_data = roi_means.tolist()
                else:
                    # Single frame case
                    frame = image_data
                    clipped_coords = shape_coords.copy()
                    clipped_coords[:, 0] = np.clip(clipped_coords[:, 0], 0, frame.shape[0]-1)
                    clipped_coords[:, 1] = np.clip(clipped_coords[:, 1], 0, frame.shape[1]-1)
                    
                    mask = np.zeros(frame.shape, dtype=bool)
                    rr, cc = polygon(clipped_coords[:, 0], clipped_coords[:, 1], frame.shape)
                    mask[rr, cc] = True
                    
                    roi_pixels = frame[mask]
                    if len(roi_pixels) > 0:
                        historical_data.append(np.mean(roi_pixels))
                    else:
                        historical_data.append(0.0)
        
        except Exception as e:
            print(f"Error extracting historical ROI data: {e}")
        
        return historical_data
    
    def update_roi_plot(self, image_data):
        """Update ROI plot with new data from Napari shapes (manual only)"""
        if not self.roi_enabled or self.roi_window is None:
            return
        
        roi_values = self.extract_napari_roi_data(image_data)
        
        if roi_values:
            # Create/update plot curves for each ROI
            for roi_name, roi_value in roi_values.items():
                # ROI data should already be populated with historical data
                # from extract_napari_roi_data method
                
                # Create/update plot curve for this ROI
                if roi_name not in self.roi_curves:
                    # Use the same color as assigned to the Napari shape
                    color = self.get_roi_color(roi_name)
                    self.roi_curves[roi_name] = self.roi_plot_widget.plot(
                        pen=pg.mkPen(color, width=2), name=roi_name
                    )
                
                # Update plot with all data (historical + current)
                if roi_name in self.roi_data and len(self.roi_data[roi_name]) > 0:
                    frame_numbers = list(range(len(self.roi_data[roi_name])))
                    self.roi_curves[roi_name].setData(frame_numbers, self.roi_data[roi_name])
            
            # Remove ROIs that no longer exist in Napari
            existing_roi_names = set(roi_values.keys())
            roi_names_to_remove = []
            for roi_name in self.roi_data.keys():
                if roi_name not in existing_roi_names:
                    roi_names_to_remove.append(roi_name)
            
            for roi_name in roi_names_to_remove:
                # Remove from data
                del self.roi_data[roi_name]
                # Remove from color mapping
                if roi_name in self.roi_color_map:
                    del self.roi_color_map[roi_name]
                # Remove from plot
                if roi_name in self.roi_curves:
                    self.roi_plot_widget.removeItem(self.roi_curves[roi_name])
                    del self.roi_curves[roi_name]
            
            # Update info label
            roi_count = len(roi_values)
            total_frames = max([len(data) for data in self.roi_data.values()]) if self.roi_data else 0
            
            self.roi_info_label.setText(
                f"Active ROIs: {roi_count} | Total frames: {total_frames} | "
                f"Current values: {', '.join([f'{name}={val:.1f}' for name, val in roi_values.items()])}"
            )
        else:
            self.roi_info_label.setText("No ROIs detected - draw shapes in Napari first")
    
    def refresh_status(self):
        """Refresh status display (called by timer)"""
        if self.viewer and self.viewer.monitoring_active:
            try:
                # Retry connecting to shapes layer if not connected yet
                if self.napari_shapes_layer is None:
                    self.retry_napari_connection()
                
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
                
                # ROI updates are now manual only - no automatic updates
                
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
        
        # Close ROI window
        if self.roi_window:
            self.roi_window.close()
        
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
    
    # Set application-wide dark palette for system dialogs
    palette = QPalette()
    palette.setColor(QPalette.Window, Qt.darkGray)
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, Qt.black)
    palette.setColor(QPalette.AlternateBase, Qt.darkGray)
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, Qt.darkGray)
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, Qt.blue)
    palette.setColor(QPalette.Highlight, Qt.blue)
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
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
