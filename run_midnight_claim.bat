@echo off
REM MidnightClaimer GUI Windows Launcher
REM User-friendly graphical interface for Midnight token claims

echo.
echo ================================================
echo MidnightClaimer GUI - Secure Token Claiming Tool
echo ================================================
echo.
echo Starting user-friendly graphical interface...
echo No administrator privileges required for GUI mode.
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python is not found in PATH. Trying python3...
    python3 --version >nul 2>&1
    if %errorLevel% neq 0 (
        echo ERROR: Python is not installed or not in PATH
        echo Please install Python 3.8+ and add it to your system PATH
        echo.
        echo Download Python from: https://python.org/downloads
        echo.
        echo Press any key to exit...
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
    )
) else (
    set PYTHON_CMD=python
)

echo Using Python command: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM Check for tkinter (required for GUI)
echo Checking GUI support...
%PYTHON_CMD% -c "import tkinter; print('GUI support available')" 2>nul
if %errorLevel% neq 0 (
    echo ERROR: Python tkinter module not found
    echo tkinter is required for the GUI interface
    echo.
    echo On Windows: Reinstall Python with "tcl/tk and IDLE" option checked
    echo On Linux: Install python3-tk package
    echo.
    echo Press any key to exit...
    pause
    exit /b 1
)

REM Install/upgrade pip
echo Updating pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet

REM Install GUI dependencies
echo Checking and installing GUI dependencies...
echo This may take a few minutes on first run...
echo.

%PYTHON_CMD% -c "import pycardano, bitcoinlib, mnemonic; from PIL import Image" 2>nul
if %errorLevel% neq 0 (
    echo Installing missing dependencies...
    echo This will install: pycardano, bitcoinlib, mnemonic, Pillow
    echo.
    
    %PYTHON_CMD% -m pip install -r requirements_gui.txt
    
    echo.
    echo Verifying installation...
    %PYTHON_CMD% -c "import pycardano, bitcoinlib, mnemonic; from PIL import Image; print('All dependencies verified successfully!')" 2>nul
    if %errorLevel% neq 0 (
        echo ERROR: Failed to install required dependencies
        echo.
        echo Please try manual installation:
        echo %PYTHON_CMD% -m pip install pycardano bitcoinlib mnemonic Pillow
        echo.
        echo Press any key to exit...
        pause
        exit /b 1
    )
    echo Dependencies installed and verified successfully!
) else (
    echo All required dependencies are already installed.
)
echo.

REM Check if GUI launcher exists
if not exist "run_gui.py" (
    echo ERROR: run_gui.py not found in current directory
    echo Please ensure you have the complete MidnightClaimer GUI package
    echo.
    echo Press any key to exit...
    pause
    exit /b 1
)

REM Display security warning
echo ========================================
echo SECURITY REMINDER
echo ========================================
echo.
echo Before using this tool:
echo  1. Create a NEW wallet and transfer funds there
echo  2. Use your OLD wallet only for claiming authorization
echo  3. Use a secure, isolated computer
echo  4. Delete all generated files after claiming
echo.
echo The GUI will guide you through the secure process.
echo ========================================
echo.

REM Ask user confirmation
echo Press any key to launch the GUI, or Ctrl+C to cancel...
pause >nul

REM Launch the GUI
echo Starting MidnightClaimer GUI...
echo.
echo Executing: %PYTHON_CMD% run_gui.py
echo Working directory: %CD%
echo.
%PYTHON_CMD% run_gui.py
echo GUI process returned with exit code: %errorLevel%

REM Check exit code
if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo GUI application closed normally
    echo ========================================
    echo.
    echo Remember to:
    echo  - Delete any generated private key files
    echo  - Clear browser cache if you imported keys
    echo  - Transfer claimed tokens to your NEW secure wallet
    echo.
) else (
    echo.
    echo ========================================
    echo GUI application closed with exit code: %errorLevel%
    echo ========================================
    echo.
    echo If you encountered issues:
    echo  - Check the midnight_claimer_gui.log file for details
    echo  - Ensure all dependencies are correctly installed
    echo  - Try running: python run_gui.py directly
    echo.
)

echo Press any key to exit...
pause