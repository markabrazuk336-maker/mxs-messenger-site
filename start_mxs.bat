@echo off
setlocal EnableExtensions

title MXS Messenger v7
cd /d "%~dp0"

if not exist "data" mkdir "data"
if not exist "data\uploads" mkdir "data\uploads"

cd /d "%~dp0backend"

echo ========================================
echo        MXS Messenger v7 launcher
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create virtual environment.
        echo Install Python and enable Add Python to PATH.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists.
)

echo [2/4] Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Could not install requirements.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [3/4] Creating .env file...
    copy ".env.example" ".env" >nul
) else (
    echo [3/4] .env already exists.
)

echo [4/4] Starting MXS server...
echo.
echo Open this URL if browser does not open automatically:
echo http://127.0.0.1:8000
echo.
echo To stop server press Ctrl+C in this window.
echo.

timeout /t 2 >nul
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
