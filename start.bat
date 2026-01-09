@echo off
chcp 65001 >nul
echo ================================
echo   股票量化选股系统
echo   新手版 v1.0
echo ================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.10+
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Python版本: %PYTHON_VERSION%

REM 检查虚拟环境
if not exist "venv\" (
    echo.
    echo 📦 首次运行，正在创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate
    echo 📥 正在安装依赖...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    call venv\Scripts\activate
)

REM 检查数据库
if not exist "data\stock_data.db" (
    echo.
    echo 🗄️  正在初始化数据库...
    if not exist "data" mkdir data
    python -c "from utils.db_helper import init_db; init_db()"
    echo ✅ 数据库初始化完成
)

echo.
echo 🚀 启动Web应用...
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   访问地址: http://localhost:8501
echo   按 Ctrl+C 停止服务
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

streamlit run app.py

pause
