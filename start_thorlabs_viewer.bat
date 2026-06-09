@echo off
echo ========================================
echo  Thorlabs Live Viewer Startup
echo ========================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Environment not found.
    echo Please double-click 'setup_windows.bat' first to install the software.
    echo.
    pause
    exit /b 1
)

echo Starting Thorlabs Live Viewer GUI...
call .venv\Scripts\activate
python thorlabs_gui_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Program exited with an error.
    pause
)

