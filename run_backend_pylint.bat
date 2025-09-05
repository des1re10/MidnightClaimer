@echo off
echo ===============================================================================
echo                    MidnightClaimer Backend Pylint Analysis
echo ===============================================================================
echo.

:: Set PYTHONPATH environment variable to include needed directories
set "PYTHONPATH=%cd%;%cd%\Src;%cd%\cardano-claim;%cd%\bitcoin-claim;%PYTHONPATH%"
echo PYTHONPATH set to: %PYTHONPATH%
echo.

:: Check if pylint is available
echo Checking pylint availability...
python -c "import pylint; print('pylint version:', pylint.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: pylint not found. Installing pylint...
    pip install pylint
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install pylint. Please install manually:
        echo   pip install pylint
        goto :error_exit
    )
)
echo.

:: Create pylint configuration if it doesn't exist
if not exist ".pylintrc" (
    echo Creating default pylint configuration...
    echo [MAIN] > .pylintrc
    echo init-hook='import sys; sys.path.append("Src")' >> .pylintrc
    echo >> .pylintrc
    echo [MESSAGES CONTROL] >> .pylintrc
    echo disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,too-few-public-methods,too-many-arguments,too-many-locals,too-many-branches,too-many-statements,line-too-long >> .pylintrc
    echo >> .pylintrc
    echo [FORMAT] >> .pylintrc
    echo max-line-length=120 >> .pylintrc
    echo.
)

:: Run pylint on main modules
echo Running pylint analysis...
echo ===============================================================================

echo Analyzing Cardano Service...
pylint --rcfile=.pylintrc Src\services\cardano_service.py > cardano_service_pylint.txt 2>&1
set cardano_result=%errorlevel%

echo Analyzing Bitcoin Service...
pylint --rcfile=.pylintrc Src\services\bitcoin_service.py > bitcoin_service_pylint.txt 2>&1
set bitcoin_result=%errorlevel%

echo Analyzing Security Utilities...
pylint --rcfile=.pylintrc Src\utils\security.py > security_pylint.txt 2>&1
set security_result=%errorlevel%

echo Analyzing GUI Main Window...
pylint --rcfile=.pylintrc Src\gui\main_window.py > gui_pylint.txt 2>&1
set gui_result=%errorlevel%

:: Analyze working scripts
echo Analyzing working Cardano script...
pylint --rcfile=.pylintrc cardano-claim\midnight_claim_cardano.py > working_cardano_pylint.txt 2>&1

echo Analyzing working Bitcoin script...
pylint --rcfile=.pylintrc bitcoin-claim\midnight_claim_bitcoin.py > working_bitcoin_pylint.txt 2>&1

:: Consolidate results
echo.
echo ===============================================================================
echo                              PYLINT RESULTS
echo ===============================================================================

echo.
echo CARDANO SERVICE:
if %cardano_result% lss 8 (
    echo ✅ PASSED - No critical issues
) else (
    echo ❌ ISSUES FOUND - Check cardano_service_pylint.txt
)
type cardano_service_pylint.txt | findstr "rated at\|Your code has been rated"

echo.
echo BITCOIN SERVICE:
if %bitcoin_result% lss 8 (
    echo ✅ PASSED - No critical issues  
) else (
    echo ❌ ISSUES FOUND - Check bitcoin_service_pylint.txt
)
type bitcoin_service_pylint.txt | findstr "rated at\|Your code has been rated"

echo.
echo SECURITY UTILITIES:
if %security_result% lss 8 (
    echo ✅ PASSED - No critical issues
) else (
    echo ❌ ISSUES FOUND - Check security_pylint.txt
)
type security_pylint.txt | findstr "rated at\|Your code has been rated"

echo.
echo GUI MAIN WINDOW:
if %gui_result% lss 8 (
    echo ✅ PASSED - No critical issues
) else (
    echo ❌ ISSUES FOUND - Check gui_pylint.txt
)
type gui_pylint.txt | findstr "rated at\|Your code has been rated"

echo.
echo ===============================================================================
echo Analysis complete. Detailed reports available:
echo - cardano_service_pylint.txt
echo - bitcoin_service_pylint.txt  
echo - security_pylint.txt
echo - gui_pylint.txt
echo - working_cardano_pylint.txt
echo - working_bitcoin_pylint.txt
echo.

:error_exit
echo Script finished. Press any key to exit...
pause >nul

:: Return appropriate exit code
if %cardano_result% geq 8 exit /b 1
if %bitcoin_result% geq 8 exit /b 1  
if %security_result% geq 8 exit /b 1
if %gui_result% geq 8 exit /b 1
exit /b 0 