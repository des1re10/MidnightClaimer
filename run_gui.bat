@echo off
REM Direct GUI Launcher - No pauses, immediate start
echo Starting MidnightClaimer GUI directly...
cd /d "%~dp0"
python run_gui.py
echo GUI closed. Press any key to exit...
pause >nul