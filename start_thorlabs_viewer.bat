@echo off
REM Thorlabs Live Viewer Startup Script
REM This script activates the napari conda environment and starts the GUI

echo ========================================
echo  Thorlabs Live Viewer Startup
echo ========================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda not found in PATH
    echo Please ensure Anaconda/Miniconda is installed and added to PATH
    echo.
    pause
    exit /b 1
)

echo [1/3] Activating napari conda environment...
call conda activate napari
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate napari environment
    echo Please ensure the 'napari' conda environment exists
    echo You can create it with: conda create -n napari napari
    echo.
    pause
    exit /b 1
)

echo [2/3] Environment activated successfully
echo Current environment: %CONDA_DEFAULT_ENV%
echo.

echo [3/3] Starting Thorlabs Live Viewer GUI...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Start the GUI application
python thorlabs_gui_app.py

REM Check if the program exited with an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Program exited with error code %ERRORLEVEL%
    echo.
    pause
) else (
    echo.
    echo Program closed successfully
)

echo.
echo Deactivating conda environment...
call conda deactivate

echo Done.
pause
