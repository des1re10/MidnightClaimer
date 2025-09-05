@echo off
echo ===============================================================================
echo                    MidnightClaimer Backend Unit Tests
echo ===============================================================================
echo.

:: Set PYTHONPATH environment variable to include needed directories
set "PYTHONPATH=%cd%;%cd%\Src;%cd%\cardano-claim;%cd%\bitcoin-claim;%PYTHONPATH%"
echo PYTHONPATH set to: %PYTHONPATH%
echo.

:: Check if pytest is available
echo Checking pytest availability...
python -c "import pytest; print('pytest version:', pytest.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: pytest not found. Installing pytest...
    pip install pytest pytest-cov pytest-mock
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install pytest. Please install manually:
        echo   pip install pytest pytest-cov pytest-mock
        goto :error_exit
    )
)
echo.

:: Check if required dependencies are available
echo Checking required dependencies...
python -c "import pycardano, bitcoinlib, mnemonic, tkinter" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Some dependencies may be missing. Tests may fail.
    echo Required packages: pycardano, bitcoinlib, mnemonic, tkinter
    echo.
)

:: Run unit tests with coverage
echo Running MidnightClaimer unit tests with coverage...
echo ===============================================================================
python -m pytest tests/ -v --tb=short --cov=Src --cov-report=term-missing --cov-report=html:htmlcov
set test_result=%errorlevel%

echo.
echo ===============================================================================

if %test_result% equ 0 (
    echo ✅ All tests passed successfully!
    echo Coverage report generated in htmlcov/index.html
) else (
    echo ❌ Some tests failed. Check output above for details.
)

echo.
echo Test Summary:
echo - Unit tests: tests/
echo - Coverage report: htmlcov/index.html
echo - Test configuration: pytest.ini
echo.

:error_exit
echo Script finished. Press any key to exit...
pause >nul
exit /b %test_result% 