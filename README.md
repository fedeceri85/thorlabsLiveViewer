# Thorlabs Live Viewer

Real-time viewer for Thorlabs microscopy data with GUI control panel and background threading.

## Overview

This application provides live monitoring of raw files being written in real-time by Thorlabs microscopy systems, with automatic Napari viewer updates and comprehensive parameter control.

## Features

- 🖥️ **GUI Control Panel**: Easy-to-use interface for parameter adjustment
- 📂 **Folder Management**: Browse and validate data folders automatically
- 🚀 **Real-time Monitoring**: Background threading for live data updates
- 📊 **Progress Tracking**: Real-time frame counting and progress bars
- ⚙️ **Parameter Control**: Adjust chunk size, wait time, and FPS settings
- 🔄 **Auto Reset**: Automatic reset when selecting new folders
- 🎬 **Test Data Generation**: Built-in test data generator for demonstration
- 🛡️ **Thread Safety**: Proper Qt-based GUI updates (macOS compatible)

## Quick Start

1. **Launch with test data:**
   ```bash
   python thorlabs_viewer.py --generate-test
   ```

2. **Launch with existing data:**
   ```bash
   python thorlabs_viewer.py --folder /path/to/your/data
   ```

3. **Launch GUI only:**
   ```bash
   python thorlabs_viewer.py
   ```

## Requirements

- Python 3.8+
- napari environment with Qt support
- Required packages: `numpy`, `napari`, `qtpy`, `skimage`

### Environment Setup

```bash
# Activate the napari environment
conda activate napari

# Install additional dependencies if needed
conda install qtpy
```

## Project Structure

```
thorlabs_viewer.py          # Main launcher
src/                        # Core application files
├── thorlabs_gui_app.py     # GUI application
├── thorlabs_live_viewer_simple.py  # Live viewer engine
├── generate_live_raw.py    # Test data generator
└── launch_gui.py           # Alternative launcher
archive/                    # Historical notebooks and experiments
sampleImage/                # Sample data files
testLiveData/               # Generated test data
```

## Usage

### GUI Application

The main GUI provides:

- **Folder Selection**: Browse button to select data folders
- **Parameter Controls**: 
  - Chunk Size: Number of frames to load per chunk (1-20)
  - Wait Time: Wait time at live edge in seconds (0.1-5.0)
  - Expected FPS: Expected frame rate for adaptive timing (1-60)
- **Control Buttons**:
  - Start Monitoring: Begin real-time monitoring
  - Stop Monitoring: Stop current monitoring
  - Restart: Restart with new parameters
- **Progress Display**: Real-time frame counting and progress bar
- **Status Log**: Comprehensive logging with timestamps

### Command Line Options

```bash
python thorlabs_viewer.py --help
```

Options:
- `--generate-test`: Generate test data before launching GUI
- `--folder PATH`: Initial folder to open in GUI
- `--info`: Show detailed application information

## Data Requirements

The application expects folders containing:
- `Image_001_001.raw`: Raw binary image data
- `ChanC_Preview.tif`: Preview image for dimensions

## Threading Architecture

The application uses a safe threading model:
- **Main Thread**: GUI updates and user interaction
- **Background Thread**: File monitoring and data loading
- **Qt Timers**: Thread-safe communication between threads

This design prevents the GUI freezing and crashes that can occur with improper threading (especially on macOS).

## Troubleshooting

### Environment Issues
```bash
# Check if in correct environment
python -c "import napari, qtpy; print('Environment OK')"

# Activate napari environment if needed
conda activate napari
```

### GUI Not Appearing
- Ensure you're in the napari environment
- Check that Qt packages are installed: `python -c "import qtpy; print('Qt OK')"`

### File Not Found Errors
- Ensure data folder contains required files (`Image_001_001.raw` and `ChanC_Preview.tif`)
- Use the test data generator if you don't have real data

## Development Notes

This application evolved from Jupyter notebook experiments to a complete standalone solution. The key improvements include:

1. **Proper Threading**: Qt-based thread-safe GUI updates
2. **macOS Compatibility**: Resolved NSWindow threading issues
3. **User Interface**: Complete GUI replacing command-line interaction
4. **Project Organization**: Clean separation of concerns

## License

Research/Educational Use

## Author

AI Assistant, August 2025
