@echo off
REM Stock Quantitative Selection System - Starter Script v1.0
echo ================================
echo   Stock Quantitative System
echo   Beginner Edition v1.0
echo ================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python version: %PYTHON_VERSION%

REM Check virtual environment
if not exist "venv\" (
    echo.
    echo [INFO] First run, creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    call venv\Scripts\activate
)

REM Check database
if not exist "data\stock_data.db" (
    echo.
    echo [INFO] Initializing database...
    if not exist "data" mkdir data
    python -c "from utils.db_helper import init_db; init_db()"
    echo [OK] Database initialized
)

echo.
echo [INFO] Starting Web application...
echo.
echo ===============================================
echo   Access URL: http://localhost:8501
echo   Press Ctrl+C to stop service
echo ===============================================
echo.

streamlit run app.py

pause
