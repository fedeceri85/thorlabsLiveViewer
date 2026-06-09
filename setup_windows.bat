@echo off
echo ========================================
echo  Thorlabs Live Viewer Setup (Windows)
echo ========================================
echo.
echo Checking for Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not added to PATH.
    echo Please install Python 3 from the Microsoft Store or python.org
    echo and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo.
echo Activating environment and installing dependencies...
echo This may take a few minutes. Please wait...
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================
echo SETUP COMPLETE!
echo You can now double-click 'start_thorlabs_viewer.bat' to launch the app.
echo ========================================
pause
