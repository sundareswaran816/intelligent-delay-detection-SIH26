@echo off
title Civiora - National File Verification Portal (SIH 2026)
color 0B
cls
echo ==============================================================================
echo       CIVIORA - National Workflow & Intelligent Delay Prevention Portal
echo                      Smart India Hackathon (SIH 2026)
echo ==============================================================================
echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python detected.
echo.

echo [2/3] Installing / Verifying required packages...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Could not install via requirements.txt, trying direct pip install...
    pip install fastapi uvicorn jinja2 python-multipart --quiet
)
echo [OK] Dependencies are ready.
echo.

echo [3/3] Starting Civiora Server on http://127.0.0.1:8000 ...
echo.
echo ------------------------------------------------------------------------------
echo Application is launching in your default web browser...
echo If the browser does not open automatically, visit: http://127.0.0.1:8000
echo.
echo Press CTRL+C in this window anytime to stop the server.
echo ------------------------------------------------------------------------------
echo.

:: Launch the cross-platform Python starter that opens the browser and runs uvicorn
python start_server.py

pause
