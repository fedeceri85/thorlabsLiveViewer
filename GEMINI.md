# GEMINI Project Documentation: Thorlabs Live Viewer

## 1. Project Overview
**Name**: Thorlabs Live Viewer
**Purpose**: A real-time visualization tool for monitoring raw microscopy data as it is being acquired by Thorlabs systems. It allows users to view live updates of `Image_001_001.raw` files in Napari without interrupting the acquisition process.

## 2. Key Components

### 2.1 Entry Points
- **`thorlabs_gui_app.py`**: The main application entry point.
  - Features: Qt-based Control Panel.
  - Role: Handles folder selection, parameter configuration (Chunk Size, Wait Time), and launches the Napari viewer.
- **`start_thorlabs_viewer.bat`**: Windows batch script to easily launch `thorlabs_gui_app.py`.
- **`start_thorlabs_viewer.sh`**: Linux/macOS shell script to launch the app using the local virtual environment.

### 2.2 Core Logic (`src/`)
- **`src/thorlabs_live_viewer_simple.py`**: The core viewer backend.
  - **Class `ThorlabsLiveViewerSimple`**: Manages the Napari viewer instance, file reading, and threading.
  - **Functionality**: Polls `Image_001_001.raw` for new data, applies optional Gaussian smoothing (supporting GPU via `cupy` if available), and updates the display via Qt Signals.
- **`src/generate_live_raw.py`**: Development tool for data simulation.
  - **Functionality**: Generates a synthetic `Image_001_001.raw` file with a growing pattern to simulate active acquisition.
  - **Usage**: Useful for testing the viewer logic without a physical microscope.

### 2.3 Data Structure
The application requires a specific folder structure for each recording session:
- **`Image_001_001.raw`**: A growing binary file containing raw 2D frames (uint16). In multi-channel experiments, frames from different channels are interleaved (even indices = Ch1, odd indices = Ch2).
- **`ChanX_Preview.tif`** (where X is A, B, C, or D): Static preview image(s) used to ascertain frame dimensions (width/height). The **number of preview files** determines the channel count (1 or 2 channels supported).

## 3. Architecture & Data Flow
1.  **Initialization**: User launches `thorlabs_gui_app.py`, which sets up the Qt application and Napari viewer.
2.  **Configuration**: User selects a data folder. The app validates the existence of `Image_001_001.raw` and at least one `ChanX_Preview.tif` (or `Experiment.xml`).
3.  **Channel Detection**: The number of `ChanX_Preview.tif` files determines single- or dual-channel mode (max 2).
4.  **Monitoring Loop**:
    - A background thread (managed by `ThorlabsLiveViewerSimple`) continuously checks the size of the raw file.
    - New frames are read in `Chunk Size` blocks (logical frames, each spanning `num_channels` raw frames).
    - Frames are deinterleaved per channel, then each channel is processed independently (e.g., Gaussian filter).
    - Per-channel data is emitted via a thread-safe Qt Signal as a `dict`.
5.  **Visualization**:
    - The main GUI thread receives the signal and updates separate Napari layers (`Ch1`, `Ch2`).
    - If ROI plotting is enabled, mean intensity values are extracted from the selected channel and plotted in real-time. A dropdown selects the target channel.

## 4. Key Libraries & Dependencies
- **Core**: `python` (3.8+), `numpy`.
- **GUI & Visualization**: `qtpy` (PyQt5/PySide2 wrapper), `napari`, `pyqtgraph`.
- **Image Processing**: `scikit-image`, `scipy` (CPU), `cupy` (GPU, optional), `pyclesperanto_prototype` (GPU, optional).

## 5. Setup & Installation
1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Launch Application**:
    ```bash
    ./start_thorlabs_viewer.sh
    ```

## 6. Usage for Developers
- **Run GUI**:
  ```bash
  python thorlabs_gui_app.py
  ```
- **Generate Test Data (in a separate terminal)**:
  ```bash
  python src/generate_live_raw.py --fps 5
  ```
- **Run without GUI (Direct Viewer)**:
  ```bash
  python src/thorlabs_live_viewer_simple.py /path/to/data_folder
  ```

## 7. Project Files Map
```
.
├── thorlabs_gui_app.py        # Main GUI Application Entry Point
├── GEMINI.md                  # This documentation
├── README.md                  # General user documentation
├── start_thorlabs_viewer.bat  # Launcher script (Windows)
├── start_thorlabs_viewer.sh   # Launcher script (Linux/macOS)
├── src/
│   ├── thorlabs_live_viewer_simple.py # Backend Viewer Logic
│   ├── generate_live_raw.py           # Test Data Generator
│   └── ...
├── archive/                   # Historical/Unused code
└── ...
```

## 8. TODO
- ~~The preview file name can either be named 'ChanC_Preview.tif' or ChanA_Preview.tif (B and D also possible). Change the code to look for which one is available. Better still, load the Experiment.xml file and extract the metadata from there: pixelX, pixelY and frameRate (see example xml file in root folder)~~ ✅ Done — `parse_experiment_xml()` reads `Experiment.xml` first, falls back to any `Chan*_Preview.tif`
- ~~Remove ROI monitor altogether if automatic is good enough.~~ ✅ Done — Manual "Update Metrics" button commented out; auto-update checkbox added
- ~~Change chunk size default to 500 and wait time to 3 s.~~ ✅ Done — Defaults changed in both GUI and backend
- In the future, add the possibility to determine the best parameters based on the frame rate of the recording. E.g., with 20 fps, 500 chunk and 3s wait is ok.