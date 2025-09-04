@echo off
REM Midnight Claim Script Runner with Admin Rights
REM This script runs the midnight_claim.py script with elevated privileges

echo ========================================
echo Midnight Token Claim Script Runner
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    echo.
) else (
    echo This script requires administrator privileges.
    echo Requesting elevation...
    echo.
    echo Press any key to continue with elevation request...
    pause
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && \"%~f0\"' -Verb RunAs"
    exit /b
)

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python is not found in PATH. Trying python3...
    python3 --version >nul 2>&1
    if %errorLevel% neq 0 (
        echo ERROR: Python is not installed or not in PATH
        echo Please install Python 3.x and add it to your system PATH
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
echo.

REM Install required Python packages
echo Checking and installing required Python packages...
%PYTHON_CMD% -c "import pycardano, dotenv, bech32" 2>nul
if %errorLevel% neq 0 (
    echo Installing missing dependencies...
    %PYTHON_CMD% -m pip install pycardano python-dotenv bech32
    if %errorLevel% neq 0 (
        echo ERROR: Failed to install required dependencies
        echo Please run: pip install pycardano python-dotenv bech32
        echo.
        echo Press any key to exit...
        pause
        exit /b 1
    )
    echo Dependencies installed successfully.
) else (
    echo All required dependencies are already installed.
)
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo.
    echo Please create a .env file with the following content:
    echo TREZOR_SEED_PHRASE='your 24 word seed phrase'
    echo TREZOR_PASSPHRASE='your passphrase'
    echo CLAIM_ADDRESS='addr1q...'
    echo CONTROLLED_STAKE_KEY='stake1...'
    echo CARDANO_CLI_PATH='C:\Users\%USERNAME%\AppData\Roaming\Cardano\cardano-cli.exe'
    echo CARDANO_NODE_SOCKET_PATH='\\.\pipe\cardano-node'
    echo.
    echo Press any key to exit...
    pause
    exit /b 1
)

REM Check if midnight_claim.py exists
if not exist "midnight_claim.py" (
    echo ERROR: midnight_claim.py not found in current directory
    echo.
    echo Press any key to exit...
    pause
    exit /b 1
)

REM Run the Python script
echo Starting Midnight Claim process...
echo.
%PYTHON_CMD% midnight_claim.py

REM Check exit code
if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo Script completed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Script completed with errors (Exit code: %errorLevel%)
    echo ========================================
)

echo.
pause