# Thorlabs Live Viewer

Real-time visualization tool for monitoring raw microscopy data as it is being acquired by Thorlabs systems.

## Overview

This application allows users to view live updates of `Image_001_001.raw` files in an integrated Napari viewer without interrupting the acquisition process. It features a modern Qt-based control panel for parameter configuration and real-time ROI (Region of Interest) intensity monitoring.

## Features

- 🖥️ **Integrated GUI**: Single-window interface combining controls, Napari viewer, and ROI plots.
- 📂 **Experiment Management**: Browse root folders and select active experiments from a dynamic dropdown.
- 🚀 **Real-time Monitoring**: Background threading for live data updates with Gaussian smoothing (GPU support via `cupy` if available).
- 📊 **ROI Monitoring**: Draw shapes in Napari to plot mean intensity values in real-time.


## Quick Start

### 1. Setup Environment

**For users without Python experience:** Please read the [Installation Guide](INSTALLATION_GUIDE.md) for simple, 1-click installation instructions.

**For developers:**
It is recommended to use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch Application

**Using Launcher Scripts:**
- **Linux/macOS:** `./start_thorlabs_viewer.sh`
- **Windows:** `start_thorlabs_viewer.bat`

**Manual Launch:**
```bash
python thorlabs_gui_app.py
```

### 3. Generate Test Data (Optional)

To test the viewer without a microscope, run the generator in a separate terminal:
```bash
python src/generate_live_raw.py --fps 5
```

## Project Structure

```
.
├── thorlabs_gui_app.py        # Main GUI Application Entry Point
├── start_thorlabs_viewer.sh   # Linux/macOS launcher
├── start_thorlabs_viewer.bat  # Windows launcher
├── requirements.txt           # Python dependencies
├── src/
│   ├── thorlabs_live_viewer_simple.py # Backend Viewer Logic
│   └── generate_live_raw.py           # Test Data Generator
├── archive/                   # Historical/Unused code
└── README.md                  # This documentation
```

## Usage

### GUI Application

1. **Select Root Folder**: Click "Browse" to select the directory containing your recordings.
2. **Select Experiment**: Choose the specific experiment folder from the dropdown.
3. **Configure Parameters**:
   - **Chunk Size**: Number of frames to load per update.
   - **Wait Time**: Interval between checks for new data.
   - **Gaussian Filter**: Enable/disable spatial smoothing.
4. **Start Monitoring**: Click "Start" to begin the live feed.
5. **ROI Monitoring**: Draw rectangles or ellipses in the Napari "Annotations" layer to automatically see intensity plots.

## Data Requirements

The application expects folders to contain:
- `Image_001_001.raw`: Growing binary file containing raw 2D frames (uint16).
- `ChanC_Preview.tif`: A static preview image used to determine frame dimensions.

## Requirements

- Python 3.8+
- Dependencies: `numpy`, `napari`, `qtpy`, `pyqtgraph`, `scikit-image`, `scipy`.
- Optional: `cupy` or `pyclesperanto_prototype` for GPU acceleration.

## Author

Federico Ceriani  
Last Updated: May 2026
