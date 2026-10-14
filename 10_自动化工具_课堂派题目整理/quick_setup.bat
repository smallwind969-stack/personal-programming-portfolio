@echo off
echo ============================================
echo Ketangpai Tool - Quick Start
echo ============================================
echo.
echo Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo.
echo [Step 1/3] Installing dependencies...
pip install -r requirements.txt

echo.
echo [Step 2/3] Installing Playwright browser...
playwright install chromium

echo.
echo [Step 3/3] Creating directories...
if not exist "data" mkdir data
if not exist "output" mkdir output
if not exist "logs" mkdir logs

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo Now run: run_source.bat
echo Or: python main.py
echo.
pause
