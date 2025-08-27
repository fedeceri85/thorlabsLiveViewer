@echo off
setlocal enabledelayedexpansion

REM Advanced Thorlabs Live Viewer Startup Script
REM Automatically detects conda installation and activates napari environment

echo ========================================
echo  Thorlabs Live Viewer - Advanced Start
echo ========================================
echo.

REM Environment name (change if different)
set ENV_NAME=napari

REM Try to find conda installation
set CONDA_FOUND=0
set CONDA_EXE=

REM Check if conda is in PATH
where conda >nul 2>nul
if !ERRORLEVEL! EQU 0 (
    set CONDA_FOUND=1
    set CONDA_EXE=conda
    echo Found conda in PATH
    goto :activate_env
)

REM Common conda installation paths
set CONDA_PATHS[0]=%USERPROFILE%\anaconda3
set CONDA_PATHS[1]=%USERPROFILE%\miniconda3
set CONDA_PATHS[2]=C:\ProgramData\Anaconda3
set CONDA_PATHS[3]=C:\ProgramData\Miniconda3
set CONDA_PATHS[4]=C:\Anaconda3
set CONDA_PATHS[5]=C:\Miniconda3

echo Searching for conda installation...
for /L %%i in (0,1,5) do (
    if exist "!CONDA_PATHS[%%i]!\Scripts\conda.exe" (
        set CONDA_FOUND=1
        set CONDA_EXE="!CONDA_PATHS[%%i]!\Scripts\conda.exe"
        echo Found conda at: !CONDA_PATHS[%%i]!
        
        REM Initialize conda for this session
        call "!CONDA_PATHS[%%i]!\Scripts\activate.bat" "!CONDA_PATHS[%%i]!"
        goto :activate_env
    )
)

if !CONDA_FOUND! EQU 0 (
    echo ERROR: Could not find conda installation
    echo.
    echo Please ensure conda is installed in one of these locations:
    echo - %USERPROFILE%\anaconda3
    echo - %USERPROFILE%\miniconda3  
    echo - C:\ProgramData\Anaconda3
    echo - C:\ProgramData\Miniconda3
    echo.
    echo Or add conda to your PATH environment variable
    echo.
    pause
    exit /b 1
)

:activate_env
echo.
echo Activating %ENV_NAME% environment...

REM Check if environment exists
!CONDA_EXE! env list | findstr /C:"%ENV_NAME%" >nul
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo ERROR: Environment '%ENV_NAME%' not found
    echo.
    echo Available environments:
    !CONDA_EXE! env list
    echo.
    echo To create napari environment, run:
    echo conda create -n napari napari pyqtgraph qtpy scikit-image
    echo.
    pause
    exit /b 1
)

REM Activate the environment
call conda activate %ENV_NAME%
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Failed to activate %ENV_NAME% environment
    pause
    exit /b 1
)

echo Environment activated: %CONDA_DEFAULT_ENV%
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if the Python script exists
if not exist "thorlabs_gui_app.py" (
    echo ERROR: thorlabs_gui_app.py not found in current directory
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

echo Starting Thorlabs Live Viewer GUI...
echo.

REM Run the application
python thorlabs_gui_app.py

REM Check exit code
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo ERROR: Application exited with error code !ERRORLEVEL!
    echo.
) else (
    echo.
    echo Application closed successfully
)

REM Deactivate environment
echo Deactivating conda environment...
call conda deactivate

echo.
echo Done.
pause
