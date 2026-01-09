# -*- coding: utf-8 -*-
"""
数据库辅助工具
提供数据库连接、初始化、查询等功能
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
import config

# ============ 数据库连接管理 ============

@contextmanager
def get_db_connection():
    """
    获取数据库连接（上下文管理器）

    使用示例:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stock_daily_history")
    """
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
    try:
        yield conn
    finally:
        conn.close()


def get_connection():
    """
    获取数据库连接（非上下文管理器版本）

    使用示例:
        conn = get_connection()
        cursor = conn.cursor()
        # ... 操作
        conn.close()
    """
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============ 数据库初始化 ============

def init_db():
    """
    初始化数据库，创建所有表和索引
    """
    print("正在初始化数据库...")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. 创建股票日线数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily_history (
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                amount REAL,
                turnover_ratio REAL,
                PRIMARY KEY (ts_code, trade_date)
            )
        """)

        # 2. 创建分钟线数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_minute_history (
                ts_code TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                frequency TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                amount REAL,
                PRIMARY KEY (ts_code, timestamp, frequency)
            )
        """)

        # 3. 创建技术指标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_indicators (
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                frequency TEXT DEFAULT 'd',
                -- MA均线
                ma5 REAL, ma10 REAL, ma20 REAL, ma60 REAL,
                -- 成交量均线
                vma5 REAL, vma10 REAL,
                -- 价格变化
                change_pct REAL,
                change_5d REAL,
                -- MACD
                dif REAL, dea REAL, macd REAL,
                -- KDJ
                k REAL, d REAL, j REAL,
                -- RSI
                rsi6 REAL, rsi12 REAL, rsi24 REAL,
                -- 布林带
                boll_upper REAL, boll_mid REAL, boll_lower REAL,
                -- ATR
                atr14 REAL,
                PRIMARY KEY (ts_code, trade_date, frequency)
            )
        """)

        # 4. 创建股票池表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL UNIQUE,
                stock_name TEXT,
                pool_name TEXT DEFAULT 'default',
                add_date DATE DEFAULT CURRENT_DATE,
                note TEXT,
                symbol TEXT,
                area TEXT,
                industry TEXT,
                list_date TEXT
            )
        """)

        # 5. 创建用户策略表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                strategy_name TEXT NOT NULL,
                strategy_type TEXT,
                template_name TEXT,
                params_json TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # 6. 创建选股历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS selection_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER,
                strategy_name TEXT,
                execute_date DATE,
                stock_pool TEXT,
                result_count INTEGER,
                results_json TEXT,
                execution_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES user_strategies(id)
            )
        """)

        # 7. 创建监控任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitor_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                condition_type TEXT,
                condition_value REAL,
                condition_json TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_check_time TIMESTAMP,
                triggered_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. 创建监控提醒表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitor_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                stock_code TEXT,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trigger_message TEXT,
                current_value REAL,
                is_read BOOLEAN DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES monitor_tasks(id)
            )
        """)

        # 9. 创建交易日历表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_trade_calendar (
                exchange TEXT NOT NULL,
                cal_date TEXT NOT NULL,
                is_open INTEGER NOT NULL,
                pretrade_date TEXT,
                PRIMARY KEY (exchange, cal_date)
            )
        """)

        # 创建索引
        _create_indexes(cursor)

        # 导入交易日历数据（如果表为空）
        cursor.execute("SELECT COUNT(*) as count FROM stock_trade_calendar")
        if cursor.fetchone()['count'] == 0:
            _import_trade_calendar(cursor)

        conn.commit()

    print("数据库初始化完成！")


def _create_indexes(cursor):
    """
    创建数据库索引以优化查询性能
    """
    # stock_daily_history 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_daily_code
        ON stock_daily_history(ts_code)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_daily_date
        ON stock_daily_history(trade_date)
    """)

    # stock_indicators 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_indicators_code
        ON stock_indicators(ts_code)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_indicators_date
        ON stock_indicators(trade_date)
    """)

    # selection_history 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_selection_date
        ON selection_history(execute_date)
    """)

    # monitor_tasks 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_monitor_active
        ON monitor_tasks(is_active)
    """)

    # monitor_alerts 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_read
        ON monitor_alerts(is_read)
    """)

    # stock_trade_calendar 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_calendar_is_open
        ON stock_trade_calendar(is_open)
    """)


def _import_trade_calendar(cursor):
    """
    导入交易日历数据

    参数:
        cursor: 数据库游标
    """
    import os
    try:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'data', 'stock_trade_calendar.csv')

        if not os.path.exists(csv_path):
            print(f"⚠️ 交易日历文件不存在: {csv_path}")
            return

        import csv
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = []
            for row in reader:
                data.append({
                    'exchange': row['exchange'],
                    'cal_date': row['cal_date'],
                    'is_open': int(row['is_open']),
                    'pretrade_date': row['pretrade_date']
                })

            # 批量插入
            cursor.executemany(
                """INSERT INTO stock_trade_calendar (exchange, cal_date, is_open, pretrade_date)
                   VALUES (?, ?, ?, ?)""",
                [(d['exchange'], d['cal_date'], d['is_open'], d['pretrade_date']) for d in data]
            )

        print(f"✅ 已导入 {len(data)} 条交易日历数据")

    except Exception as e:
        print(f"❌ 导入交易日历失败: {e}")


def get_latest_trade_date(target_date=None):
    """
    获取最近的交易日

    参数:
        target_date: 目标日期，格式 'YYYY-MM-DD'，默认为今天

    返回:
        str: 最近的交易日，格式 'YYYY-MM-DD'
              如果 target_date 是交易日，返回 target_date
              如果 target_date 是非交易日，返回之前的最近交易日
    """
    from datetime import datetime

    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')

    try:
        with get_db_connection() as conn:
            # 查询小于等于目标日期的最近交易日
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cal_date
                FROM stock_trade_calendar
                WHERE cal_date <= ? AND is_open = 1
                ORDER BY cal_date DESC
                LIMIT 1
            """, (target_date,))

            result = cursor.fetchone()
            if result:
                return result['cal_date']
            else:
                # 如果没找到，返回目标日期（容错）
                return target_date

    except Exception as e:
        print(f"❌ 获取交易日失败: {e}")
        return target_date


def is_trade_date(date_str):
    """
    判断指定日期是否为交易日

    参数:
        date_str: 日期字符串，格式 'YYYY-MM-DD'

    返回:
        bool: True表示是交易日，False表示非交易日
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT is_open
                FROM stock_trade_calendar
                WHERE cal_date = ?
                LIMIT 1
            """, (date_str,))

            result = cursor.fetchone()
            if result:
                return result['is_open'] == 1
            return False

    except Exception as e:
        print(f"❌ 判断交易日失败: {e}")
        return False


def get_previous_trade_date(date_str):
    """
    获取指定日期之前的上一个交易日

    参数:
        date_str: 日期字符串，格式 'YYYY-MM-DD'

    返回:
        str: 上一个交易日，格式 'YYYY-MM-DD'
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pretrade_date
                FROM stock_trade_calendar
                WHERE cal_date = ?
                LIMIT 1
            """, (date_str,))

            result = cursor.fetchone()
            if result and result['pretrade_date']:
                return result['pretrade_date']

            # 如果没有找到，查询最近的小于指定日期的交易日
            cursor.execute("""
                SELECT cal_date
                FROM stock_trade_calendar
                WHERE cal_date < ? AND is_open = 1
                ORDER BY cal_date DESC
                LIMIT 1
            """, (date_str,))

            result = cursor.fetchone()
            if result:
                return result['cal_date']

            return None

    except Exception as e:
        print(f"❌ 获取上一交易日失败: {e}")
        return None


# ============ 数据库查询辅助函数 ============

def execute_query(sql, params=None, fetch_one=False, fetch_all=False):
    """
    执行SQL查询

    参数:
        sql: SQL语句
        params: 参数元组
        fetch_one: 是否只获取一条记录
        fetch_all: 是否获取所有记录

    返回:
        查询结果
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.rowcount


def execute_insert(table_name, data):
    """
    执行插入操作

    参数:
        table_name: 表名
        data: 字典格式的数据

    返回:
        插入的行ID
    """
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(data.values()))
        conn.commit()
        return cursor.lastrowid


def execute_update(table_name, data, where_clause, where_params=None):
    """
    执行更新操作

    参数:
        table_name: 表名
        data: 字典格式的更新数据
        where_clause: WHERE子句
        where_params: WHERE参数

    返回:
        影响的行数
    """
    set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
    sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"

    params = tuple(data.values())
    if where_params:
        params += tuple(where_params)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount


def execute_delete(table_name, where_clause, where_params=None):
    """
    执行删除操作

    参数:
        table_name: 表名
        where_clause: WHERE子句
        where_params: WHERE参数

    返回:
        删除的行数
    """
    sql = f"DELETE FROM {table_name} WHERE {where_clause}"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if where_params:
            cursor.execute(sql, where_params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor.rowcount


# ============ 数据库状态检查 ============

def check_db_exists():
    """检查数据库文件是否存在"""
    import os
    return os.path.exists(config.DB_PATH)


def get_db_info():
    """
    获取数据库信息

    返回:
        数据库信息字典
    """
    info = {
        'db_path': config.DB_PATH,
        'db_exists': check_db_exists(),
        'table_count': 0,
        'tables': []
    }

    if info['db_exists']:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            info['table_count'] = len(tables)
            info['tables'] = [t['name'] for t in tables]

            # 获取每个表的记录数
            for table in info['tables']:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                info[f'{table}_count'] = count

    return info


# ============ 批量操作优化 ============

def execute_batch_insert(table_name, data_list):
    """
    批量插入数据（性能优化）

    参数:
        table_name: 表名
        data_list: 数据字典列表

    返回:
        插入的行数
    """
    if not data_list:
        return 0

    columns = ', '.join(data_list[0].keys())
    placeholders = ', '.join(['?' for _ in data_list[0]])
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 使用executemany进行批量插入
        cursor.executemany(sql, [tuple(d.values()) for d in data_list])
        conn.commit()
        return cursor.rowcount


def execute_batch_update(table_name, data_list, key_column):
    """
    批量更新数据（性能优化）

    参数:
        table_name: 表名
        data_list: 数据字典列表
        key_column: 作为更新条件的列名

    返回:
        更新的行数
    """
    if not data_list:
        return 0

    # 构建UPDATE语句
    first_item = data_list[0]
    update_columns = [k for k in first_item.keys() if k != key_column]
    set_clause = ', '.join([f"{col} = ?" for col in update_columns])
    sql = f"UPDATE {table_name} SET {set_clause} WHERE {key_column} = ?"

    updated_count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for data in data_list:
            # 准备参数值
            values = [data[col] for col in update_columns]
            values.append(data[key_column])
            cursor.execute(sql, tuple(values))
            updated_count += cursor.rowcount
        conn.commit()

    return updated_count


# ============ 数据清理优化 ============

def vacuum_database():
    """
    优化数据库（清理碎片，减小文件大小）

    返回:
        操作是否成功
    """
    try:
        with get_db_connection() as conn:
            conn.execute("VACUUM")
            conn.commit()
        return True
    except Exception as e:
        print(f"数据库优化失败: {e}")
        return False


def analyze_database():
    """
    分析数据库并更新统计信息（优化查询计划）

    返回:
        操作是否成功
    """
    try:
        with get_db_connection() as conn:
            # 分析所有表
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for table in tables:
                conn.execute(f"ANALYZE {table['name']}")

            conn.commit()
        return True
    except Exception as e:
        print(f"数据库分析失败: {e}")
        return False


# ============ 数据库备份 ============

def backup_database(backup_path=None):
    """
    备份数据库

    参数:
        backup_path: 备份文件路径，默认在data/backups/目录

    返回:
        备份文件路径或None（失败时）
    """
    import os
    import shutil
    from datetime import datetime

    if not check_db_exists():
        return None

    # 生成备份路径
    if backup_path is None:
        backup_dir = os.path.join(os.path.dirname(config.DB_PATH), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'stock_data_backup_{timestamp}.db')

    try:
        shutil.copy2(config.DB_PATH, backup_path)
        return backup_path
    except Exception as e:
        print(f"数据库备份失败: {e}")
        return None


# ============ 事务管理 ============

@contextmanager
def get_db_transaction():
    """
    获取数据库事务（上下文管理器）

    使用示例:
        with get_db_transaction() as (conn, cursor):
            cursor.execute("INSERT INTO ...")
            cursor.execute("UPDATE ...")
            # 如果发生异常，自动回滚
            # 否则自动提交
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield conn, cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ============ 查询性能优化 ============

def execute_query_paginated(sql, params=None, page=1, page_size=100):
    """
    执行分页查询

    参数:
        sql: SQL语句
        params: 参数元组
        page: 页码（从1开始）
        page_size: 每页记录数

    返回:
        (记录列表, 总页数, 总记录数)
    """
    # 计算总数
    count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as subquery"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(count_sql, params)
        else:
            cursor.execute(count_sql)
        total = cursor.fetchone()['total']

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # 执行分页查询
    offset = (page - 1) * page_size
    paginated_sql = f"{sql} LIMIT {page_size} OFFSET {offset}"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(paginated_sql, params)
        else:
            cursor.execute(paginated_sql)
        records = cursor.fetchall()

    return records, total_pages, total


def execute_query_with_cache(sql, params=None, cache_key=None, ttl=300):
    """
    执行带缓存的查询（需要配合缓存装饰器使用）

    参数:
        sql: SQL语句
        params: 参数元组
        cache_key: 缓存键
        ttl: 缓存时间（秒）

    返回:
        查询结果
    """
    # 简单实现：直接查询，建议使用streamlit的@st.cache_data装饰器
    return execute_query(sql, params, fetch_all=True)


# ============ 数据完整性检查 ============

def check_data_integrity():
    """
    检查数据完整性

    返回:
        完整性检查结果字典
    """
    result = {
        'status': 'OK',
        'issues': []
    }

    if not check_db_exists():
        result['status'] = 'ERROR'
        result['issues'].append('数据库文件不存在')
        return result

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 检查是否有重复数据
        cursor.execute("""
            SELECT ts_code, trade_date, COUNT(*) as count
            FROM stock_daily_history
            GROUP BY ts_code, trade_date
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            result['status'] = 'WARNING'
            result['issues'].append(f'发现{len(duplicates)}条重复的日线数据')

        # 检查数据缺失
        cursor.execute("""
            SELECT COUNT(DISTINCT ts_code) as stock_count
            FROM stock_daily_history
        """)
        stock_count = cursor.fetchone()['stock_count']

        if stock_count == 0:
            result['status'] = 'WARNING'
            result['issues'].append('股票日线数据为空')

    return result


# ============ 数据统计 ============

def get_data_statistics():
    """
    获取数据统计信息

    返回:
        统计信息字典
    """
    stats = {}

    if not check_db_exists():
        return stats

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 日线数据统计
        cursor.execute("""
            SELECT
                COUNT(DISTINCT ts_code) as stock_count,
                COUNT(*) as record_count,
                MIN(trade_date) as min_date,
                MAX(trade_date) as max_date
            FROM stock_daily_history
        """)
        daily_stats = cursor.fetchone()
        stats['daily'] = dict(daily_stats) if daily_stats else {}

        # 指标数据统计
        cursor.execute("""
            SELECT
                COUNT(DISTINCT ts_code) as stock_count,
                COUNT(*) as record_count,
                MIN(trade_date) as min_date,
                MAX(trade_date) as max_date
            FROM stock_indicators
            WHERE frequency = 'd'
        """)
        indicator_stats = cursor.fetchone()
        stats['indicators'] = dict(indicator_stats) if indicator_stats else {}

        # 股票池统计
        cursor.execute("""
            SELECT
                pool_name,
                COUNT(*) as count
            FROM stock_pool
            GROUP BY pool_name
        """)
        pool_stats = cursor.fetchall()
        stats['pools'] = {s['pool_name']: s['count'] for s in pool_stats}

        # 策略统计
        cursor.execute("""
            SELECT
                strategy_type,
                COUNT(*) as count
            FROM user_strategies
            WHERE is_active = 1
            GROUP BY strategy_type
        """)
        strategy_stats = cursor.fetchall()
        stats['strategies'] = {s['strategy_type'] or '未分类': s['count'] for s in strategy_stats}

    return stats


# ============ 测试代码 ============

if __name__ == "__main__":
    print("=" * 50)
    print("数据库工具测试")
    print("=" * 50)

    # 初始化数据库
    init_db()

    # 显示数据库信息
    print("\n数据库信息:")
    info = get_db_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
