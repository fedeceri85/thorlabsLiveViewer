# Quick Installation Guide

Welcome! You do not need to know any programming to install and use the **Thorlabs Live Viewer**. Just follow these simple steps depending on your computer.

---

## 🟦 Windows Users

### Step 1: Install Python
If you don't already have Python installed, you need to download it:
1. Go to the [Python Download Page](https://www.python.org/downloads/).
2. Click the yellow **Download Python** button.
3. Open the downloaded installer file.
4. **⚠️ CRITICAL STEP:** At the bottom of the installation window, check the box that says **"Add python.exe to PATH"** before you click Install Now.

### Step 2: Install the App
1. Download this software folder to your computer and unzip it.
2. Open the folder and **double-click `setup_windows.bat`**.
3. A black window will appear and download the required files. This will take a few minutes. Wait until it says "SETUP COMPLETE!" and press any key to close it.

### Step 3: Run the App
- Whenever you want to use the software, simply **double-click `start_thorlabs_viewer.bat`**.

---

## 🍎 Mac Users

### Step 1: Install Python
If you don't already have Python installed:
1. Go to the [Python Download Page](https://www.python.org/downloads/).
2. Click the yellow **Download Python** button.
3. Open the downloaded package and complete the installation wizard.

### Step 2: Install the App
1. Download this software folder to your Mac and unzip it.
2. Open the folder, right-click (or Control-click) on **`setup_mac.command`**, and select **Open**. (If your Mac shows a warning about it being from an unidentified developer, click "Open" anyway).
3. A terminal window will open and download the necessary files. Wait until it says "SETUP COMPLETE!".

### Step 3: Run the App
- Whenever you want to use the software, simply **double-click `start_mac.command`**.

---

## 🐧 Linux Users
1. Ensure `python3` and `python3-venv` are installed via your package manager (e.g., `sudo apt install python3 python3-venv`).
2. Run the setup script: `./setup_mac.command` (it works for Linux too).
3. Launch the app: `./start_thorlabs_viewer.sh`.

---

## ⚡ Advanced: Optional GPU Acceleration & AI Features

If you have a powerful NVIDIA graphics card, you can enable hardware acceleration to speed up image smoothing (Gaussian filters) and enable AI-based automatic segmentation (Cellpose).

### How to Enable:
1. **Install NVIDIA CUDA Toolkit (Windows/Linux only)**
   - Download the **CUDA Toolkit 12.x** from the [NVIDIA Website](https://developer.nvidia.com/cuda-downloads).
   - Follow the standard installer instructions for your operating system.

2. **Enable the Requirements**
   - Open the `requirements.txt` file in this folder using any text editor (like Notepad).
   - Find the lines that say `# cupy-cuda12x` and `# cellpose` at the bottom.
   - Delete the `#` and the space at the start of those lines so they just say `cupy-cuda12x` and `cellpose`.
   - Save the file.

3. **Re-run the Setup Script**
   - Double-click the `setup_windows.bat` (or `setup_mac.command`) script again. It will read the updated `requirements.txt` and download the heavy GPU/AI packages.
   - Once it says "SETUP COMPLETE!", launch the app normally. The advanced features will now be unlocked!
