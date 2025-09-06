@echo off
echo 🌙 MidnightClaimer - Simple Step-by-Step GUI
echo ============================================
echo.

REM Change to the directory where this batch file is located
cd /d "%~dp0"
echo 📁 Working directory: %CD%
echo.

REM Check if we're in the right directory
if not exist "simple_gui.py" (
    echo ❌ Error: simple_gui.py not found in current directory
    echo Please ensure you're running this from the MidnightClaimer folder
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if required folders exist
if not exist "cardano-claim" (
    echo ❌ Error: cardano-claim folder not found
    echo Please ensure you're running this from the MidnightClaimer root directory
    pause
    exit /b 1
)

if not exist "bitcoin-claim" (
    echo ❌ Error: bitcoin-claim folder not found  
    echo Please ensure you're running this from the MidnightClaimer root directory
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found: 
python --version

REM Check if tkinter is available
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ tkinter is not available
    echo Please install tkinter or use Python with tkinter support
    echo.
    echo For Windows, tkinter should be included with Python
    echo Try reinstalling Python from https://python.org
    pause
    exit /b 1
)

echo ✅ tkinter is available
echo.

REM Run the simple GUI
echo ✅ Starting simple GUI...
python simple_gui.py

echo.
pause