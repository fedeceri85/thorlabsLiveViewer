@echo off
REM Simple Thorlabs Live Viewer Startup Script
REM Edit the environment name below if different

REM ============ CONFIGURATION ============
REM Change this to your conda environment name
SET ENV_NAME=napari

REM Change this if your conda is installed elsewhere
SET CONDA_PATH=%USERPROFILE%\anaconda3
REM Alternative common paths:
REM SET CONDA_PATH=%USERPROFILE%\miniconda3
REM SET CONDA_PATH=C:\ProgramData\Anaconda3

REM =======================================

echo Starting Thorlabs Live Viewer...
echo Environment: %ENV_NAME%
echo.

REM Initialize conda for this session
call "%CONDA_PATH%\Scripts\activate.bat" "%CONDA_PATH%"

REM Activate the environment
call conda activate %ENV_NAME%

REM Change to script directory and run
cd /d "%~dp0"
python thorlabs_gui_app.py

REM Deactivate when done
call conda deactivate

pause
