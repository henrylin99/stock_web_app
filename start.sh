#!/bin/bash

echo "================================"
echo "  股票量化选股系统"
echo "  新手版 v1.0"
echo "================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.10+"
    echo "   下载地址: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ Python版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 首次运行，正在创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 正在安装依赖..."
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
else
    source venv/bin/activate
fi

# 检查数据库
if [ ! -f "data/stock_data.db" ]; then
    echo ""
    echo "🗄️  正在初始化数据库..."
    python3 -c "from utils.db_helper import init_db; init_db()"
    echo "✅ 数据库初始化完成"
fi

echo ""
echo "🚀 启动Web应用..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  访问地址: http://localhost:8501"
echo "  按 Ctrl+C 停止服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

streamlit run app.py
