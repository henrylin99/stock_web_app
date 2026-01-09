# -*- coding: utf-8 -*-
"""
baostock数据客户端封装
提供股票数据下载功能
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import time
import config


# ============ baostock客户端类 ============

class BaostockClient:
    """
    baostock客户端封装类

    功能:
    - 自动登录/登出管理
    - 股票数据下载
    - 错误处理和重试机制
    """

    def __init__(self):
        """初始化客户端"""
        self._lg = None
        self.is_logged_in = False

    def login(self):
        """
        登录baostock

        返回:
            bool: 登录是否成功
        """
        if self.is_logged_in:
            return True

        self._lg = bs.login()

        if self._lg.error_code == '0':
            self.is_logged_in = True
            return True
        else:
            print(f"登录失败: {self._lg.error_msg}")
            return False

    def logout(self):
        """登出baostock"""
        if self.is_logged_in:
            bs.logout()
            self.is_logged_in = False
            self._lg = None

    def __enter__(self):
        """上下文管理器入口"""
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.logout()

    # ============ 数据获取方法 ============

    def download_stock_data(self, stock_code, start_date, end_date, frequency="d", adjustflag="2"):
        """
        下载股票数据

        参数:
            stock_code: 股票代码 (如: sh.600000, sz.000001)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            frequency: 数据周期 (d=日线, 60m=60分钟, 30m=30分钟, 15m=15分钟, 5m=5分钟)
            adjustflag: 复权类型 (1=后复权, 2=前复权, 3=不复权)

        返回:
            DataFrame: 股票数据，失败返回None
        """
        if not self.is_logged_in:
            if not self.login():
                return None

        # 转换股票代码格式 (600000.SH -> sh.600000)
        code = self._convert_code_format(stock_code, reverse=True)

        # 转换频率格式: 60m -> 60, 30m -> 30, 15m -> 15, 5m -> 5
        # baostock API 要求分钟线使用数字格式，不带 'm' 后缀
        bs_frequency = frequency
        if frequency.endswith('m'):
            bs_frequency = frequency.replace('m', '')

        # 选择字段：分钟线数据不支持 'turn'（换手率）字段，但需要 'time' 字段来区分不同时段
        # 日线支持的字段更多，分钟线需要 date 和 time 来组成完整时间戳
        if bs_frequency == 'd':
            fields = "date,open,high,low,close,volume,amount,turn"
        else:
            fields = "date,time,open,high,low,close,volume,amount"

        # 获取数据
        rs = bs.query_history_k_data_plus(
            code,
            fields,
            start_date=start_date,
            end_date=end_date,
            frequency=bs_frequency,
            adjustflag=adjustflag
        )

        if rs.error_code != '0':
            print(f"获取数据失败: {rs.error_msg}")
            return None

        # 转换为DataFrame
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return None

        df = pd.DataFrame(data_list, columns=rs.fields)

        # 处理分钟线的时间戳：将 date 和 time 合并成完整的 timestamp
        if 'time' in df.columns:
            # time 字段格式: '20250103103000000' -> 需要转换为 '2025-01-03 10:30:00'
            def parse_baostock_time(time_str):
                """解析 baostock 时间格式: 20250103103000000 -> 2025-01-03 10:30:00"""
                try:
                    time_str = str(time_str)
                    if len(time_str) >= 14:
                        year = time_str[0:4]
                        month = time_str[4:6]
                        day = time_str[6:8]
                        hour = time_str[8:10]
                        minute = time_str[10:12]
                        second = time_str[12:14]
                        return f"{year}-{month}-{day} {hour}:{minute}:{second}"
                    return time_str
                except:
                    return time_str

            # 创建完整的 timestamp 列
            df['date'] = df['time'].apply(parse_baostock_time)
            df.drop('time', axis=1, inplace=True)

        # 转换数据类型并进行精度控制
        df['code'] = stock_code  # 添加股票代码列

        # 价格字段：保留2位小数（A股价格最小变动单位0.01元）
        df['open'] = pd.to_numeric(df['open'], errors='coerce').round(2)
        df['high'] = pd.to_numeric(df['high'], errors='coerce').round(2)
        df['low'] = pd.to_numeric(df['low'], errors='coerce').round(2)
        df['close'] = pd.to_numeric(df['close'], errors='coerce').round(2)

        # 成交量：整数（手），先填充 NaN 为 0 再转换
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)

        # 成交额：保留2位小数（元），NaN 填充为 0
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).round(2)

        # turn（换手率）字段只在日线数据中存在，保留4位小数，NaN 填充为 0
        if 'turn' in df.columns:
            df['turn'] = pd.to_numeric(df['turn'], errors='coerce').fillna(0).round(4)

        return df

    def download_batch_stocks(self, stock_codes, start_date, end_date, frequency="d",
                              progress_callback=None, delay=0.5):
        """
        批量下载股票数据

        参数:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据周期
            progress_callback: 进度回调函数 callback(current, total, stock_code)
            delay: 每次请求之间的延迟（秒）

        返回:
            dict: {stock_code: DataFrame}
        """
        results = {}
        total = len(stock_codes)

        for i, code in enumerate(stock_codes):
            if progress_callback:
                progress_callback(i + 1, total, code)

            df = self.download_stock_data(code, start_date, end_date, frequency)
            if df is not None and not df.empty:
                results[code] = df

            # 延迟，避免请求过快
            if i < total - 1:
                time.sleep(delay)

        return results

    def get_stock_basic_info(self, stock_code):
        """
        获取股票基本信息

        参数:
            stock_code: 股票代码

        返回:
            dict: 股票基本信息
        """
        if not self.is_logged_in:
            if not self.login():
                return None

        code = self._convert_code_format(stock_code, reverse=True)

        rs = bs.query_stock_basic(code=code)

        if rs.error_code != '0':
            return None

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return None

        return {
            'code': stock_code,
            'name': data_list[0][1] if len(data_list[0]) > 1 else '',
            'industry': data_list[0][2] if len(data_list[0]) > 2 else '',
        }

    def get_all_stocks(self):
        """
        获取所有股票列表

        返回:
            DataFrame: 股票列表
        """
        if not self.is_logged_in:
            if not self.login():
                return None

        rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))

        if rs.error_code != '0':
            return None

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return None

        df = pd.DataFrame(data_list, columns=rs.fields)
        df['code'] = df['code'].apply(lambda x: self._convert_code_format(x))
        return df

    # ============ 工具方法 ============

    @staticmethod
    def _convert_code_format(code, reverse=False):
        """
        转换股票代码格式

        参数:
            code: 股票代码
            reverse: True=baostock格式(sh.600000), False=标准格式(600000.SH)

        返回:
            str: 转换后的代码
        """
        if not reverse:
            # sh.600000 -> 600000.SH
            if '.' in code:
                prefix, number = code.split('.')
                market = 'SH' if prefix == 'sh' else 'SZ'
                return f"{number}.{market}"
            return code
        else:
            # 600000.SH -> sh.600000
            if '.' in code:
                number, market = code.split('.')
                prefix = market.lower()
                return f"{prefix}.{number}"
            return code

    @staticmethod
    def validate_code_format(code):
        """
        验证股票代码格式

        参数:
            code: 股票代码

        返回:
            bool: 格式是否正确
        """
        # 支持两种格式: 600000.SH 或 sh.600000
        if '.' in code:
            parts = code.split('.')
            if len(parts) == 2:
                if parts[0].isdigit() and parts[1] in ['SH', 'SZ']:
                    return True
                if parts[1].isdigit() and parts[0] in ['sh', 'sz']:
                    return True
        return False


# ============ 便捷函数 ============

def download_stock_data(stock_code, start_date, end_date, frequency="d"):
    """
    便捷函数：下载单只股票数据

    参数:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        frequency: 数据周期

    返回:
        DataFrame: 股票数据
    """
    with BaostockClient() as client:
        return client.download_stock_data(stock_code, start_date, end_date, frequency)


def get_stock_list():
    """
    便捷函数：获取所有股票列表

    返回:
        DataFrame: 股票列表
    """
    with BaostockClient() as client:
        return client.get_all_stocks()


# ============ 测试代码 ============

if __name__ == "__main__":
    print("=" * 50)
    print("baostock客户端测试")
    print("=" * 50)

    # 测试登录
    client = BaostockClient()
    if client.login():
        print("✅ 登录成功")

        # 测试获取股票列表
        print("\n获取股票列表...")
        stocks = client.get_all_stocks()
        if stocks is not None:
            print(f"✅ 共 {len(stocks)} 只股票")
            print(stocks.head(10))

        # 测试下载单只股票
        print("\n下载平安银行数据...")
        data = client.download_stock_data(
            '000001.SZ',
            '2023-12-01',
            '2023-12-31'
        )
        if data is not None:
            print(f"✅ 获取 {len(data)} 条数据")
            print(data.head())

        client.logout()
    else:
        print("❌ 登录失败")
