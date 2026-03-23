#!/usr/bin/env python3
"""
Thorlabs Live Viewer GUI
=========================

Qt GUI application for controlling the Thorlabs Live Viewer with
easy parameter input and folder selection.

Features:
- Single window interface with integrated Napari viewer and ROI plot
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
import glob
sys.path.append('./src')
import threading
import time
from pathlib import Path

from qtpy.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                           QSpinBox, QDoubleSpinBox, QFileDialog, QTextEdit,
                           QGroupBox, QGridLayout, QMessageBox, QProgressBar,
                           QCheckBox, QTabWidget, QSplitter, QComboBox)
from qtpy.QtCore import QTimer, QObject, Signal, Qt, QFileSystemWatcher
from qtpy.QtGui import QFont, QIcon, QPalette

import pyqtgraph as pg
import numpy as np
import napari
# Import internal Napari widgets to reconstruct the UI
try:
    from napari.qt import QtViewer
except ImportError:
    print("Warning: Could not import Napari QtViewer")
    QtViewer = None

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
        self.viewer_backend = None
        self.current_folder = None
        
        # Enable ROI monitoring by default
        self.roi_enabled = True
        self.roi_data = {}  # Dictionary to store data for multiple ROIs
        self.napari_shapes_layer = None
        self.roi_dirty = False # Flag to trigger full recalculation
        self.last_roi_frame_index = 0 # Track last processed frame
        
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
        
        # Initialize Napari Viewer (hidden/embedded)
        # We create it here so we can embed it in the layout immediately
        self.napari_viewer = napari.Viewer(show=False)
        self.napari_viewer.theme = 'dark'
        
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
        
        QSplitter::handle {
            background-color: #555555;
        }
        """
        
        self.setStyleSheet(dark_stylesheet)
        
        # Configure PyQtGraph for dark theme
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#ffffff')
        pg.setConfigOption('antialias', True)
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Thorlabs Live Viewer - Integrated View (Dark Mode)")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout (Horizontal: Control Panel | Visualization)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- LEFT PANEL (Control Panel) ---
        # Occupies 1/4 of width (stretch factor 1)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("🔬 Live Control")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)
        
        # Folder selection group
        folder_group = QGroupBox("📂 Data Selection")
        folder_layout = QGridLayout(folder_group)
        
        # Row 1: Parent Directory
        folder_layout.addWidget(QLabel("Root Folder:"), 0, 0)
        self.root_folder_edit = QLineEdit()
        self.root_folder_edit.setPlaceholderText("Select root data folder...")
        self.root_folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.root_folder_edit, 0, 1)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_root_folder)
        folder_layout.addWidget(self.browse_button, 0, 2)
        
        # Row 2: Experiment Dropdown
        folder_layout.addWidget(QLabel("Experiment:"), 1, 0)
        self.experiment_combo = QComboBox()
        self.experiment_combo.setPlaceholderText("Select experiment...")
        self.experiment_combo.currentIndexChanged.connect(self.on_experiment_selected)
        folder_layout.addWidget(self.experiment_combo, 1, 1, 1, 2)
        
        left_layout.addWidget(folder_group)

        # File watcher for refreshing experiment list
        self.fs_watcher = QFileSystemWatcher(self)
        self.fs_watcher.directoryChanged.connect(self.refresh_experiment_list)
        
        # Parameters group
        params_group = QGroupBox("⚙️ Parameters")
        params_layout = QGridLayout(params_group)
        
        # Chunk size
        params_layout.addWidget(QLabel("Chunk Size:"), 0, 0)
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 5000)
        self.chunk_size_spin.setValue(500)
        self.chunk_size_spin.setToolTip("Number of frames to load per chunk")
        params_layout.addWidget(self.chunk_size_spin, 0, 1)
        
        # Wait time
        params_layout.addWidget(QLabel("Wait Time (s):"), 1, 0)
        self.wait_time_spin = QDoubleSpinBox()
        self.wait_time_spin.setRange(0.1, 120)
        self.wait_time_spin.setValue(3.0)
        self.wait_time_spin.setSingleStep(0.5)
        self.wait_time_spin.setDecimals(1)
        self.wait_time_spin.setToolTip("Wait time at live edge")
        params_layout.addWidget(self.wait_time_spin, 1, 1)
        
        # Gaussian filter toggle
        self.gaussian_checkbox = QCheckBox("🌟 Apply Gaussian Filter")
        self.gaussian_checkbox.setChecked(True)  # Default to enabled
        params_layout.addWidget(self.gaussian_checkbox, 2, 0, 1, 2)
        
        left_layout.addWidget(params_group)
        
        # ROI Monitoring group
        roi_group = QGroupBox("📊 ROI Monitor")
        roi_layout = QGridLayout(roi_group)
        
        # Enable ROI monitoring checkbox
        self.roi_enable_checkbox = QCheckBox("Enable ROI Plot")
        self.roi_enable_checkbox.setChecked(True) # Default on
        self.roi_enable_checkbox.toggled.connect(self.toggle_roi_monitoring)
        roi_layout.addWidget(self.roi_enable_checkbox, 0, 0)

        # Auto-update ROIs checkbox
        self.auto_roi_checkbox = QCheckBox("Auto-update ROIs")
        self.auto_roi_checkbox.setChecked(True)
        self.auto_roi_checkbox.setToolTip("Update ROI plot automatically when new frames arrive")
        roi_layout.addWidget(self.auto_roi_checkbox, 0, 1)
        
        # Channel selector for ROI computation
        roi_layout.addWidget(QLabel("ROI Channel:"), 2, 0)
        self.roi_channel_combo = QComboBox()
        self.roi_channel_combo.addItem("Ch1")
        self.roi_channel_combo.setToolTip("Select which channel to compute ROI intensities on")
        self.roi_channel_combo.currentIndexChanged.connect(self._on_roi_channel_changed)
        roi_layout.addWidget(self.roi_channel_combo, 2, 1)
        # Hide channel selector by default (single channel)
        self.roi_channel_label = roi_layout.itemAtPosition(2, 0).widget()
        self.roi_channel_label.setVisible(False)
        self.roi_channel_combo.setVisible(False)
        
        # Info label
        roi_info = QLabel("Draw shapes in Napari to create ROIs")
        roi_info.setStyleSheet("color: #aaaaaa; font-style: italic; font-size: 10px")
        roi_info.setWordWrap(True)
        roi_layout.addWidget(roi_info, 3, 0, 1, 2)
        
        # Checkboxes for toggling Napari Layers (optional future feature)
        # self.show_napari_cb = QCheckBox("Show Napari")
        # self.show_napari_cb.setChecked(True)
        # roi_layout.addWidget(self.show_napari_cb, 4, 0)
        
        # Manual update (commented out - auto-update ROIs checkbox replaces this)
        # self.update_roi_button = QPushButton("🔄 Update Metrics")
        # self.update_roi_button.clicked.connect(self.manual_roi_update)
        # roi_layout.addWidget(self.update_roi_button, 4, 0, 1, 2)
        
        left_layout.addWidget(roi_group)
        
        # Snapshot group (Average last N frames)
        snapshot_group = QGroupBox("📸 Snapshot")
        snapshot_layout = QHBoxLayout(snapshot_group)
        
        snapshot_layout.addWidget(QLabel("N frames:"))
        self.avg_n_frames_spin = QSpinBox()
        self.avg_n_frames_spin.setRange(1, 10000)
        self.avg_n_frames_spin.setValue(100)
        self.avg_n_frames_spin.setToolTip("Number of recent frames to average")
        snapshot_layout.addWidget(self.avg_n_frames_spin)
        
        self.avg_button = QPushButton("📸 Average last frames")
        self.avg_button.clicked.connect(self.average_last_n_frames)
        self.avg_button.setToolTip("Average the last N acquired frames and display in Napari")
        snapshot_layout.addWidget(self.avg_button)
        
        left_layout.addWidget(snapshot_group)
        
        # Control buttons
        control_group = QGroupBox("🎮 Controls")
        control_layout = QVBoxLayout(control_group)
        
        self.start_button = QPushButton("🚀 Start")
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet("font-size: 14px; padding: 10px;")
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("🛑 Stop")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("font-size: 14px; padding: 10px;")
        control_layout.addWidget(self.stop_button)
        
        self.restart_button = QPushButton("🔄 Restart")
        self.restart_button.clicked.connect(self.restart_monitoring)
        self.restart_button.setEnabled(False)
        control_layout.addWidget(self.restart_button)
        
        left_layout.addWidget(control_group)
        
        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Idle")
        self.progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_label)
        
        left_layout.addWidget(progress_group)
        
        # Status display
        status_group = QGroupBox("Log")
        status_layout = QVBoxLayout(status_group)
        
        self.status_display = QTextEdit()
        self.status_display.setFont(QFont("Courier", 9))
        self.status_display.append("GUI Ready")
        status_layout.addWidget(self.status_display)
        
        left_layout.addWidget(status_group)
        
        # Add Stretch to push everything up
        # left_layout.addStretch()
        
        # --- RIGHT PANEL (Visualization) ---
        # Occupies 3/4 of width (stretch factor 3)
        # Use QSplitter for resizable panels
        self.right_splitter = QSplitter(Qt.Vertical)
        
        # 1. Napari Window Embedding (Complete QMainWindow)
        self.napari_container = QWidget()
        napari_layout = QHBoxLayout(self.napari_container)
        napari_layout.setContentsMargins(0,0,0,0)
        
        try:
             # Get the actual QMainWindow from Napari
             napari_main_window = self.napari_viewer.window._qt_window
             
             # Clean up: Remove from any previous parent if needed (though it's usually top-level)
             # Important: We must convert it to a widget type to be embedded
             napari_main_window.setWindowFlags(Qt.Widget)
             
             # Add to our layout
             napari_layout.addWidget(napari_main_window)
             print("✅ Embedded Napari Main Window")
             
        except Exception as e:
            print(f"❌ Error embedding Napari window: {e}")
            # Fallback (Just Canvas)
            self.napari_canvas = self.napari_viewer.window.qt_viewer
            napari_layout.addWidget(self.napari_canvas)
        
        self.right_splitter.addWidget(self.napari_container)
        
        # 2. ROI Plot Widget
        self.roi_plot_widget = pg.PlotWidget(title="ROI Intensities")
        self.roi_plot_widget.setLabel('left', 'Mean Intensity', units='AU')
        self.roi_plot_widget.setLabel('bottom', 'Frame Number')
        self.roi_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.roi_plot_widget.addLegend()
        self.roi_curves = {}
        
        self.right_splitter.addWidget(self.roi_plot_widget)
        
        # Set initial sizes (2/3 Napari, 1/3 Plot)
        # We need to set this after the widget is shown or use a timer, 
        # but setting proportional sizes works reasonably well with large enough numbers
        self.right_splitter.setSizes([600, 300])
        self.right_splitter.setCollapsible(0, False) # Don't collapse Napari
        self.right_splitter.setCollapsible(1, True)  # Allow collapsing plot
        
        # --- ADD TO MAIN LAYOUT ---
        main_layout.addWidget(left_panel, 1)      # Stretch factor 1
        main_layout.addWidget(self.right_splitter, 3) # Stretch factor 3
        
    def browse_root_folder(self):
        """Open folder selection dialog for root directory"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Root Data Folder",
            str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.set_root_folder(folder)

    def set_root_folder(self, folder):
        """Set the root folder and populate experiment list"""
        # Remove previous paths from watcher
        if self.fs_watcher.directories():
            self.fs_watcher.removePaths(self.fs_watcher.directories())
            
        self.current_folder = folder # Store root temporarily
        self.root_folder_edit.setText(folder)
        
        # Add new path to watcher
        self.fs_watcher.addPath(folder)
        
        self.refresh_experiment_list()
        self.log_status(f"📂 Root set to: {os.path.basename(folder)}")

    def refresh_experiment_list(self, path=None):
        """Scan root folder for valid experiment subfolders"""
        root = self.root_folder_edit.text()
        if not root or not os.path.exists(root):
            return

        # Get list of subdirectories
        try:
            subdirs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
            subdirs.sort()
            
            # Current selection
            current_selection = self.experiment_combo.currentText()
            
            # Helper to check if folder is a valid experiment
            def is_valid_experiment(path):
                raw = os.path.join(path, "Image_001_001.raw")
                # We relax the condition slightly to allow selecting folders that are being created
                return os.path.exists(raw)

            # Filter or mark valid experiments? For now list all folders but maybe add icon
            # Or just list all folders to be safe.
            
            # Update combo box cleanly
            if self.experiment_combo.count() != len(subdirs):
                # If count changed, reload all (simplest approach)
                 self.experiment_combo.blockSignals(True)
                 self.experiment_combo.clear()
                 self.experiment_combo.addItems(subdirs)
                 
                 # Restore selection if possible
                 idx = self.experiment_combo.findText(current_selection)
                 if idx >= 0:
                     self.experiment_combo.setCurrentIndex(idx)
                 
                 self.experiment_combo.blockSignals(False)
                 
            else:
                 # Check content match to be sure
                 existing = [self.experiment_combo.itemText(i) for i in range(self.experiment_combo.count())]
                 if existing != subdirs:
                     self.experiment_combo.blockSignals(True)
                     self.experiment_combo.clear()
                     self.experiment_combo.addItems(subdirs)
                     # Restore selection
                     idx = self.experiment_combo.findText(current_selection)
                     if idx >= 0: self.experiment_combo.setCurrentIndex(idx)
                     self.experiment_combo.blockSignals(False)

        except Exception as e:
            print(f"Error scanning folders: {e}")

    def on_experiment_selected(self, index):
        """Handle selection of an experiment folder"""
        if index < 0: return
        
        exp_name = self.experiment_combo.itemText(index)
        root = self.root_folder_edit.text()
        full_path = os.path.join(root, exp_name)
        
        self.set_experiment_folder(full_path)

    def set_experiment_folder(self, folder):
        """Set the current experiment folder and validate it"""
        self.current_folder = folder
        
        # Reset any existing backend
        if self.viewer_backend:
            self.stop_monitoring()
            self.viewer_backend.close()
            self.viewer_backend = None
            self.napari_shapes_layer = None
        
        # Validate folder: need raw file + either Experiment.xml or any Chan*_Preview.tif
        raw_file = os.path.join(folder, "Image_001_001.raw")
        has_xml = os.path.exists(os.path.join(folder, "Experiment.xml"))
        has_preview = len(glob.glob(os.path.join(folder, "Chan*_Preview.tif"))) > 0
        
        if os.path.exists(raw_file) and (has_xml or has_preview):
            source = "XML" if has_xml else "Preview TIF"
            self.log_status(f"✅ Selected: {os.path.basename(folder)} ({source})")
            self.start_button.setEnabled(True)
            self.napari_viewer.title = f"Viewer: {os.path.basename(folder)}"
            
            # Auto-start monitoring? optional.
            # self.start_monitoring() 
        else:
            self.log_status(f"⚠️  Waiting for files in {os.path.basename(folder)}...")
            self.start_button.setEnabled(False)
    
    def start_monitoring(self):
        """Start live monitoring"""
        if not self.current_folder:
            return
        
        try:
            # Initialize backend if needed
            if self.viewer_backend is None:
                self.log_status("Initializing backend...")
                # Pass existing napari viewer to backend
                self.viewer_backend = ThorlabsLiveViewerSimple(
                    self.current_folder, 
                    viewer=self.napari_viewer
                )
            
            # Start monitoring
            chunk_size = self.chunk_size_spin.value()
            wait_time = self.wait_time_spin.value()
            use_gaussian = self.gaussian_checkbox.isChecked()
            
            self.log_status(f"Started: Chunk={chunk_size}")
            self.viewer_backend.start_live_monitoring(chunk_size, wait_time, use_gaussian_filter=use_gaussian)

            # Populate channel dropdown
            self._populate_channel_dropdown()

            # Connect backend data signal to ROI update logic
            self.viewer_backend.updater.data_ready.connect(self.on_data_ready)

            # Connect to Napari shapes layer
            self.connect_to_napari_shapes()

            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.restart_button.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(self.viewer_backend.nFrames)
            self.progress_label.setText("Monitoring...")
            
        except Exception as e:
            self.log_status(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to start:\n{e}")
    
    def stop_monitoring(self):
        """Stop live monitoring"""
        if self.viewer_backend:
            self.log_status("Stopping...")
            self.viewer_backend.stop_monitoring()
            
            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.restart_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.progress_label.setText("Stopped")
            
            self.log_status("Stopped")
    
    def restart_monitoring(self):
        """Restart monitoring with current parameters"""
        if self.viewer_backend:
            self.log_status("Restarting...")
            self.napari_shapes_layer = None
            
            chunk_size = self.chunk_size_spin.value()
            wait_time = self.wait_time_spin.value()
            use_gaussian = self.gaussian_checkbox.isChecked()
            
            self.viewer_backend.restart_monitoring(chunk_size, wait_time, use_gaussian_filter=use_gaussian)
            self.connect_to_napari_shapes()
            self.log_status("Restarted")
    
    def toggle_roi_monitoring(self, enabled):
        """Toggle ROI monitoring on/off"""
        self.roi_enabled = enabled
        self.right_splitter.setSizes([700, 300 if enabled else 0])
        
        if enabled:
            self.log_status("ROI Plot Enabled")
            # Clear previous data
            self.roi_data = {}
            self.roi_color_map = {}
            self.color_index = 0
            self.roi_dirty = True
            self.last_roi_frame_index = 0
        else:
            self.log_status("ROI Plot Disabled")
    
    def _populate_channel_dropdown(self):
        """Populate ROI channel dropdown from the backend's channel list."""
        if not self.viewer_backend:
            return
        ch_names = self.viewer_backend.channel_names
        self.roi_channel_combo.blockSignals(True)
        self.roi_channel_combo.clear()
        self.roi_channel_combo.addItems(ch_names)
        self.roi_channel_combo.blockSignals(False)
        
        multi = len(ch_names) > 1
        self.roi_channel_label.setVisible(multi)
        self.roi_channel_combo.setVisible(multi)
    
    def _on_roi_channel_changed(self, index):
        """Handle ROI channel selection change — trigger full recalculation."""
        self.roi_dirty = True
        self.last_roi_frame_index = 0
        self.roi_data = {}
        # Immediately recalculate with current data if available
        if self.viewer_backend and hasattr(self.viewer_backend, 'arrays'):
            selected_ch = self.roi_channel_combo.currentText()
            if selected_ch in self.viewer_backend.arrays:
                self.update_roi_plot(self.viewer_backend.arrays[selected_ch])
    
    def connect_to_napari_shapes(self):
        """Connect to Napari's shapes layer for ROI monitoring"""
        # (Simplified logic - re-uses existing robust connection logic ideally)
        if not self.viewer_backend: return
        
        # Try to find 'Annotations' layer
        found = False
        for layer in self.napari_viewer.layers:
            if layer.name == 'Annotations':
                self.napari_shapes_layer = layer
                # Connect events
                layer.events.data.connect(self.on_shapes_changed)
                layer.events.highlight.connect(self.on_shapes_changed) # sometimes needed
                found = True
                self.log_status("Linked to ROI layer")
                
                # Reset tracking
                self.roi_dirty = True
                self.last_roi_frame_index = 0
                break
        
        if not found and len(self.napari_viewer.layers) > 0:
            # Fallback
            pass
            
    def on_shapes_changed(self, event):
        """Called when shapes are modified in Napari"""
        if self.roi_enabled:
            # Mark as dirty to trigger full recalculation on next update
            self.roi_dirty = True
            self.update_shape_colors()
    
    def update_shape_colors(self):
        """Update Napari shape colors"""
        if not self.napari_shapes_layer: return
        try:
            n_shapes = len(self.napari_shapes_layer.data)
            if n_shapes > 0:
                edge_colors = []
                for i in range(n_shapes):
                    roi_name = f"ROI_{i}"
                    if roi_name not in self.roi_color_map:
                        color = self.roi_colors[self.color_index % len(self.roi_colors)]
                        self.roi_color_map[roi_name] = color
                        self.color_index += 1
                    
                    hex_color = self.roi_color_map[roi_name]
                    rgb = [int(hex_color[1:3], 16)/255, int(hex_color[3:5], 16)/255, int(hex_color[5:7], 16)/255, 1.0]
                    edge_colors.append(rgb)
                
                self.napari_shapes_layer.edge_color = edge_colors
        except:
            pass
            
    def manual_roi_update(self):
        """Manually update ROI data"""
        if self.viewer_backend and hasattr(self.viewer_backend, 'arrays'):
             selected_ch = self.roi_channel_combo.currentText()
             if selected_ch in self.viewer_backend.arrays:
                 self.update_roi_plot(self.viewer_backend.arrays[selected_ch])
             self.log_status("Updated ROI Data")

    def average_last_n_frames(self):
        """Average the last N frames from the livestream and display in Napari"""
        if not self.viewer_backend or not hasattr(self.viewer_backend, 'arrays'):
            self.log_status("⚠️  No data loaded yet")
            return
        
        n = self.avg_n_frames_spin.value()
        
        for ch_name, data in self.viewer_backend.arrays.items():
            if data.size == 0:
                continue
            total = data.shape[0]
            n_actual = min(n, total)
            
            avg_frame = np.mean(data[-n_actual:], axis=0)
            
            # Add or update the averaged layer in Napari
            layer_name = f"Average (last N) - {ch_name}"
            existing = None
            for layer in self.napari_viewer.layers:
                if layer.name == layer_name:
                    existing = layer
                    break
            
            _ch_colormaps = {'Ch1': 'green', 'Ch2': 'red'}
            cmap = _ch_colormaps.get(ch_name, 'gray')
            if existing is not None:
                existing.data = avg_frame
            else:
                self.napari_viewer.add_image(
                    avg_frame, name=layer_name,
                    colormap=cmap, blending='additive'
                )
        
        total_frames = self.viewer_backend.arrays[self.viewer_backend.channel_names[0]].shape[0]
        n_actual = min(n, total_frames)
        self.log_status(f"📸 Averaged last {n_actual} frames (of {total_frames} total)")

    def on_data_ready(self, data):
        """Called when backend has new data ready.
        
        Args:
            data: dict mapping channel name to np.ndarray stack.
        """
        if self.roi_enabled and self.auto_roi_checkbox.isChecked():
            # Get the selected channel for ROI computation
            selected_ch = self.roi_channel_combo.currentText()
            if selected_ch in data:
                self.update_roi_plot(data[selected_ch])

    def update_roi_plot(self, image_data):
        """Update ROI plot with new data"""
        if not self.roi_enabled or image_data is None or image_data.size == 0:
            return
            
        if self.napari_shapes_layer is None:
            self.connect_to_napari_shapes()
            # If still None, try to get it from viewer again (maybe user created it)
            if self.napari_shapes_layer is None:
                 for layer in self.napari_viewer.layers:
                    if layer.name == 'Annotations':
                        self.napari_shapes_layer = layer
                        layer.events.data.connect(self.on_shapes_changed)
                        self.roi_dirty = True
                        break
            if self.napari_shapes_layer is None: return

        try:
            # Handle Dirty State (ROI Changed)
            if self.roi_dirty:
                self.roi_data = {}
                self.last_roi_frame_index = 0
                # We will process from 0 to end
                self.roi_dirty = False
                
            total_frames = len(image_data)
            start_frame = self.last_roi_frame_index
            
            # If we are somehow ahead (shouldn't happen unless reset), reset
            if start_frame > total_frames:
                start_frame = 0
                self.roi_data = {}
            
            # Nothing new to process
            if start_frame == total_frames:
                return

            # Get shapes once
            shapes_data = self.napari_shapes_layer.data
            if len(shapes_data) == 0:
                self.last_roi_frame_index = total_frames
                self.roi_plot_widget.clear()
                return

            # Prepare data structure
            for i in range(len(shapes_data)):
                roi_name = f"ROI_{i}"
                if roi_name not in self.roi_data:
                    self.roi_data[roi_name] = []

            # Optimization: Pre-compute masks for simple shapes if possible
            # For now, just iterate. Speed should be fine for typical ROI counts.
            
            # We need to process image_data[start_frame : total_frames]
            # If image_data is (N, H, W)
            
            new_chunk = image_data[start_frame:total_frames]
            
            # Iterate over shapes
            from skimage.draw import polygon
            
            # Cache masks for this update
            masks = []
            valid_shapes = []
            
            for i, shape in enumerate(shapes_data):
                 if len(shape) >= 3:
                     # Create mask
                     # Note: shape coordinates are (row, col)
                     # We assume image dimensions match the last frame
                     # This might fail if image size changes, but that shouldn't happen live
                     H, W = image_data[0].shape
                     r, c = polygon(shape[:, 0], shape[:, 1], (H, W))
                     
                     if len(r) > 0:
                         masks.append((r, c))
                         valid_shapes.append(i)
            
            if not masks:
                self.last_roi_frame_index = total_frames
                return
                
            # Compute means for the chunk
            # Vectorized approach: 
            # We want mean intensity for each ROI for each frame in new_chunk.
            
            # Loop over frames in chunk
            for frame_idx in range(len(new_chunk)):
                frame = new_chunk[frame_idx]
                
                for k, (r, c) in enumerate(masks):
                    shape_idx = valid_shapes[k]
                    roi_name = f"ROI_{shape_idx}"
                    
                    mean_val = np.mean(frame[r, c])
                    self.roi_data[roi_name].append(mean_val)
            
            # Update index
            self.last_roi_frame_index = total_frames
            
            # Update plot
            self.roi_plot_widget.clear()
            for roi_name, data in self.roi_data.items():
                if roi_name in self.roi_color_map:
                    color = self.roi_color_map[roi_name]
                    # Plot full history
                    self.roi_plot_widget.plot(data, pen=pg.mkPen(color, width=2), name=roi_name)
                    
        except Exception as e:
            # print(f"ROI Update Error: {e}")
            pass

    def update_status_display(self, message):
        """Update status log"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_display.append(f"[{timestamp}] {message}")
        # Scroll to bottom
        sb = self.status_display.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def log_status(self, message):
        """Log status message via signal"""
        self.status_updater.status_update.emit(message)
        
    def update_progress(self, current, total):
        """Update progress bar"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current}/{total} frames")
        
    def refresh_status(self):
        """Periodic status refresh"""
        if self.viewer_backend:
            status = self.viewer_backend.get_status()
            self.update_progress(status['frames_loaded'], status['total_frames'])


def main():
    app = QApplication(sys.argv)
    
    # Set app icon if available
    # app.setWindowIcon(QIcon('icon.png'))
    
    gui = ThorlabsGUI()
    gui.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
