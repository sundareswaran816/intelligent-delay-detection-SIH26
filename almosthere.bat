@echo off
title Civiora - Application & File Delay Detection Intelligence Portal (SIH 2026)
color 0B
cls
echo ==============================================================================
echo       CIVIORA - Application & File Delay Detection Intelligence Portal
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

echo [2/3] Installing / Verifying dependencies (FastAPI, Uvicorn, Jinja2, Multipart)...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    pip install fastapi uvicorn jinja2 python-multipart --quiet
)
echo [OK] Dependencies verified and ready.
echo.

echo [3/3] Starting Civiora Server on http://127.0.0.1:8000 ...
echo.
echo ------------------------------------------------------------------------------
echo Opening portal in your default web browser...
echo If the browser does not open automatically, visit: http://127.0.0.1:8000
echo.
echo Press CTRL+C in this terminal window anytime to stop the server.
echo ------------------------------------------------------------------------------
echo.

:: Launch auto-browser opener and server
python almosthere.py

pause
