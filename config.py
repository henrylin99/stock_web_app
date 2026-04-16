# -*- coding: utf-8 -*-
"""
股票量化选股系统 - 配置文件
"""

import os


def _resolve_seed_file(env_name, primary_path, fallback_path):
    """优先使用显式环境变量，其次使用目标数据目录，最后回退到仓库内置种子文件。"""
    env_value = os.getenv(env_name)
    if env_value:
        return os.path.abspath(env_value)
    if os.path.exists(primary_path):
        return os.path.abspath(primary_path)
    return os.path.abspath(fallback_path)


# ============ 项目路径 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
REPO_DATA_DIR = os.path.join(BASE_DIR, 'data')
DATA_DIR = os.path.abspath(os.getenv('DATA_DIR', REPO_DATA_DIR))
CACHE_DIR = os.path.abspath(os.getenv('CACHE_DIR', os.path.join(DATA_DIR, 'cache')))
EXPORT_DIR = os.path.abspath(os.getenv('EXPORT_DIR', os.path.join(DATA_DIR, 'exports')))
LOG_DIR = os.path.abspath(os.getenv('LOG_DIR', os.path.join(BASE_DIR, 'logs')))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# ============ 数据库配置 ============
DB_PATH = os.path.abspath(os.getenv('DB_PATH', os.path.join(DATA_DIR, 'stock_data.db')))
TRADE_CALENDAR_CSV = _resolve_seed_file(
    'TRADE_CALENDAR_CSV',
    os.path.join(DATA_DIR, 'stock_trade_calendar.csv'),
    os.path.join(REPO_DATA_DIR, 'stock_trade_calendar.csv'),
)
STOCK_BASIC_CSV = _resolve_seed_file(
    'STOCK_BASIC_CSV',
    os.path.join(DATA_DIR, 'stock_basic.csv'),
    os.path.join(REPO_DATA_DIR, 'stock_basic.csv'),
)
SCREENER_DATA_FILE = _resolve_seed_file(
    'SCREENER_DATA_FILE',
    os.path.join(DATA_DIR, 'data.parquet'),
    os.path.join(REPO_DATA_DIR, 'data.parquet'),
)
SCREENER_FIELD_DICT_FILE = os.path.abspath(
    os.getenv(
        'SCREENER_FIELD_DICT_FILE',
        os.path.join(DOCS_DIR, '宽表数据字典.md')
    )
)

# ============ baostock配置 ============
BAOSTOCK_URL = "http://baostock.com/selenium/api"

# ============ Streamlit配置 ============
STREAMLIT_PORT = 8501
STREAMLIT_HOST = "localhost"
STREAMLIT_TITLE = "股票量化选股系统"
STREAMLIT_ICON = "📈"

# ============ 应用配置 ============
APP_NAME = "股票量化选股系统"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "新手友好的股票量化选股工具"

# ============ 数据周期配置 ============
FREQUENCIES = {
    'd': '日线',
    '60m': '60分钟',
    '30m': '30分钟',
    '15m': '15分钟',
    '5m': '5分钟'
}

# ============ 技术指标配置 ============
MA_PERIODS = [5, 10, 20, 60]
VMA_PERIODS = [5, 10]
RSI_PERIODS = [6, 12, 24]

# ============ 日志配置 ============
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# ============ 确保目录存在 ============
for dir_path in [DATA_DIR, CACHE_DIR, EXPORT_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)
