@echo off
setlocal
cd /d "%~dp0"

echo MidnightClaimer - Cardano NIGHT Redemption
echo ===========================================
echo.

set "MIDNIGHT_PYTHON="

rem Prefer a repository-local environment, then inspect every Python on PATH.
call :try_python "%~dp0.venv\Scripts\python.exe"
for /f "delims=" %%P in ('where python 2^>nul') do call :try_python "%%P"

if not defined MIDNIGHT_PYTHON (
    echo ERROR: No Python 3.10+ installation with all required packages was found.
    echo Install the packages for one Python installation, for example:
    echo   py -3.12 -m pip install -r cardano-claim\requirements_cardano.txt
    pause
    exit /b 1
)

echo Using Python: %MIDNIGHT_PYTHON%
"%MIDNIGHT_PYTHON%" simple_gui.py
set "MIDNIGHT_EXIT_CODE=%errorlevel%"
echo.
if not "%MIDNIGHT_EXIT_CODE%"=="0" echo MidnightClaimer ended with exit code %MIDNIGHT_EXIT_CODE%.
pause
exit /b %MIDNIGHT_EXIT_CODE%

:try_python
if defined MIDNIGHT_PYTHON exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import sys, tkinter, requests, nacl, pycardano, cbor2, trezorlib; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 set "MIDNIGHT_PYTHON=%~1"
exit /b 0
