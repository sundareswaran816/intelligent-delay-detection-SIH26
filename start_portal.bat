@echo off
echo ===================================================
echo   Civiora - SIH 2026 Government Portal Launcher
echo ===================================================
echo.
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python 3.10+ from python.org
    pause
    exit /b
)

echo Installing required packages...
python -m pip install -r requirements.txt

echo.
echo Starting Civiora Web Application Server...
echo Open your browser at: http://127.0.0.1:8000
echo.
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
