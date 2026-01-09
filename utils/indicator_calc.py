# -*- coding: utf-8 -*-
"""
技术指标计算工具
提供常用技术指标的计算函数
"""

import pandas as pd
import numpy as np


def calculate_ma(df, periods=None):
    """
    计算移动平均线 (MA)

    参数:
        df: DataFrame，必须包含 close 列
        periods: 周期列表，默认 [5, 10, 20, 60]

    返回:
        DataFrame，添加了 ma5, ma10, ma20, ma60 列
    """
    if periods is None:
        periods = [5, 10, 20, 60]

    df = df.copy()

    for period in periods:
        df[f'ma{period}'] = df['close'].rolling(window=period, min_periods=1).mean()

    return df


def calculate_vma(df, periods=None):
    """
    计算成交量移动平均线 (VMA)

    参数:
        df: DataFrame，必须包含 volume 列
        periods: 周期列表，默认 [5, 10]

    返回:
        DataFrame，添加了 vma5, vma10 列
    """
    if periods is None:
        periods = [5, 10]

    df = df.copy()

    for period in periods:
        df[f'vma{period}'] = df['volume'].rolling(window=period, min_periods=1).mean()

    return df


def calculate_change(df):
    """
    计算涨跌幅

    参数:
        df: DataFrame，必须包含 close 列

    返回:
        DataFrame，添加了 change_pct, change_5d, change_10d 列
    """
    df = df.copy()

    # 日涨跌幅
    df['change_pct'] = df['close'].pct_change() * 100

    # 5日涨跌幅
    df['change_5d'] = df['close'].pct_change(5) * 100

    # 10日涨跌幅
    df['change_10d'] = df['close'].pct_change(10) * 100

    return df


def calculate_amplitude(df):
    """
    计算振幅

    参数:
        df: DataFrame，必须包含 high, low, close 列

    返回:
        DataFrame，添加了 amplitude 列
    """
    df = df.copy()

    # 前一日收盘价
    df['prev_close'] = df['close'].shift(1)

    # 振幅 = (最高价 - 最低价) / 前一日收盘价 * 100
    df['amplitude'] = (df['high'] - df['low']) / df['prev_close'] * 100

    # 删除临时列
    df = df.drop(columns=['prev_close'])

    return df


def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    计算MACD指标

    参数:
        df: DataFrame，必须包含 close 列
        fast: 快线周期，默认12
        slow: 慢线周期，默认26
        signal: 信号线周期，默认9

    返回:
        DataFrame，添加了 dif, dea, macd 列
    """
    df = df.copy()

    # 计算EMA
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()

    # DIF = 快线 - 慢线
    df['dif'] = df['ema_fast'] - df['ema_slow']

    # DEA = DIF的EMA
    df['dea'] = df['dif'].ewm(span=signal, adjust=False).mean()

    # MACD = (DIF - DEA) * 2
    df['macd'] = (df['dif'] - df['dea']) * 2

    # 删除临时列
    df = df.drop(columns=['ema_fast', 'ema_slow'])

    return df


def calculate_kdj(df, n=9, m1=3, m2=3):
    """
    计算KDJ指标

    参数:
        df: DataFrame，必须包含 high, low, close 列
        n: RSV周期，默认9
        m1: K值平滑系数，默认3
        m2: D值平滑系数，默认3

    返回:
        DataFrame，添加了 k, d, j 列
    """
    df = df.copy()

    # 计算RSV
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()

    # 避免除零
    denominator = high_list - low_list
    denominator = denominator.replace(0, np.nan)

    df['rsv'] = (df['close'] - low_list) / denominator * 100
    df['rsv'] = df['rsv'].fillna(50)  # 填充NaN值

    # 计算K值
    df['k'] = df['rsv']
    for i in range(1, len(df)):
        df.loc[df.index[i], 'k'] = (2/3) * df.loc[df.index[i-1], 'k'] + (1/3) * df.loc[df.index[i], 'rsv']

    # 计算D值
    df['d'] = df['k']
    for i in range(1, len(df)):
        df.loc[df.index[i], 'd'] = (2/3) * df.loc[df.index[i-1], 'd'] + (1/3) * df.loc[df.index[i], 'k']

    # 计算J值
    df['j'] = 3 * df['k'] - 2 * df['d']

    # 删除临时列
    df = df.drop(columns=['rsv'])

    return df


def calculate_rsi(df, periods=None):
    """
    计算RSI指标

    参数:
        df: DataFrame，必须包含 close 列
        periods: 周期列表，默认 [6, 12, 24]

    返回:
        DataFrame，添加了 rsi6, rsi12, rsi24 列
    """
    if periods is None:
        periods = [6, 12, 24]

    df = df.copy()

    # 计算价格变化
    delta = df['close'].diff()

    # 分离上涨和下跌
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # 计算RSI
    for period in periods:
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        # 避免除零
        rs = avg_gain / avg_loss.replace(0, np.nan)

        df[f'rsi{period}'] = 100 - (100 / (1 + rs))

        # 填充NaN值
        df[f'rsi{period}'] = df[f'rsi{period}'].fillna(50)

    return df


def calculate_boll(df, n=20, k=2):
    """
    计算布林带 (BOLL)

    参数:
        df: DataFrame，必须包含 close 列
        n: 周期，默认20
        k: 标准差倍数，默认2

    返回:
        DataFrame，添加了 boll_upper, boll_mid, boll_lower 列
    """
    df = df.copy()

    # 中轨 = MA
    df['boll_mid'] = df['close'].rolling(window=n, min_periods=1).mean()

    # 标准差
    std = df['close'].rolling(window=n, min_periods=1).std()

    # 上轨 = 中轨 + k * 标准差
    df['boll_upper'] = df['boll_mid'] + k * std

    # 下轨 = 中轨 - k * 标准差
    df['boll_lower'] = df['boll_mid'] - k * std

    return df


def calculate_atr(df, n=14):
    """
    计算真实波幅 (ATR)

    参数:
        df: DataFrame，必须包含 high, low, close 列
        n: 周期，默认14

    返回:
        DataFrame，添加了 atr14 列
    """
    df = df.copy()

    # 前一日收盘价
    df['prev_close'] = df['close'].shift(1)

    # 计算真实波幅TR
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['prev_close'])
    tr3 = abs(df['low'] - df['prev_close'])

    df['tr'] = tr1.combine(tr2, max).combine(tr3, max)

    # ATR = TR的移动平均
    df[f'atr{n}'] = df['tr'].rolling(window=n, min_periods=1).mean()

    # 删除临时列
    df = df.drop(columns=['prev_close', 'tr'])

    return df


def calculate_extended_indicators(df):
    """
    计算扩展技术指标

    参数:
        df: DataFrame，必须包含 open, high, low, close, volume, change_pct 列

    返回:
        DataFrame，添加了扩展指标
    """
    df = df.copy()

    # 1. 历史高低点
    df['max_high_5d'] = df['high'].rolling(window=5, min_periods=1).max().round(2)
    df['max_high_10d'] = df['high'].rolling(window=10, min_periods=1).max().round(2)
    df['max_high_20d'] = df['high'].rolling(window=20, min_periods=1).max().round(2)
    df['max_high_60d'] = df['high'].rolling(window=60, min_periods=1).max().round(2)

    df['max_low_5d'] = df['low'].rolling(window=5, min_periods=1).min().round(2)
    df['max_low_10d'] = df['low'].rolling(window=10, min_periods=1).min().round(2)
    df['max_low_20d'] = df['low'].rolling(window=20, min_periods=1).min().round(2)
    df['max_low_60d'] = df['low'].rolling(window=60, min_periods=1).min().round(2)

    # 2. 前一日数据
    df['prev_close'] = df['close'].shift(1).round(2)
    df['prev_high'] = df['high'].shift(1).round(2)
    df['prev_low'] = df['low'].shift(1).round(2)
    df['prev_volume'] = df['volume'].shift(1).fillna(0).astype(int)
    if 'change_pct' in df.columns:
        df['prev_change_pct'] = df['change_pct'].shift(1).round(2)
    else:
        df['prev_change_pct'] = None

    # 3. 连续统计（优化版：避免循环）
    # 计算连续上涨天数
    is_up = (df['close'] > df['open']).astype(int)
    df['consecutive_up_days'] = 0
    current_streak = 0
    for i in range(len(df)):
        if is_up.iloc[i] == 1:
            current_streak += 1
        else:
            current_streak = 0
        df.loc[df.index[i], 'consecutive_up_days'] = current_streak
    df['consecutive_up_days'] = df['consecutive_up_days'].astype(int)

    # 计算连续下跌天数
    is_down = (df['close'] < df['open']).astype(int)
    df['consecutive_down_days'] = 0
    current_streak = 0
    for i in range(len(df)):
        if is_down.iloc[i] == 1:
            current_streak += 1
        else:
            current_streak = 0
        df.loc[df.index[i], 'consecutive_down_days'] = current_streak
    df['consecutive_down_days'] = df['consecutive_down_days'].astype(int)

    # 4. K线形态
    df['body'] = abs(df['close'] - df['open']).round(2)
    df['full_range'] = (df['high'] - df['low']).round(2)

    df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)).round(2)
    df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']).round(2)

    # 避免除零
    df['body_ratio'] = (df['body'] / df['full_range'].replace(0, np.nan)).round(4)
    df['upper_shadow_ratio'] = (df['upper_shadow'] / df['full_range'].replace(0, np.nan)).round(4)
    df['lower_shadow_ratio'] = (df['lower_shadow'] / df['full_range'].replace(0, np.nan)).round(4)

    # 5. 位置指标
    df['position_20d'] = ((df['close'] - df['max_low_20d']) /
                           (df['max_high_20d'] - df['max_low_20d'])).round(4)
    df['position_60d'] = ((df['close'] - df['max_low_60d']) /
                           (df['max_high_60d'] - df['max_low_60d'])).round(4)

    return df


def calculate_all_indicators(df):
    """
    计算所有技术指标

    参数:
        df: DataFrame，必须包含 open, high, low, close, volume 列

    返回:
        DataFrame，包含所有技术指标
    """
    df = df.copy()

    # MA均线
    df = calculate_ma(df)

    # VMA成交量均线
    df = calculate_vma(df)

    # 涨跌幅
    df = calculate_change(df)

    # 振幅
    df = calculate_amplitude(df)

    # MACD
    df = calculate_macd(df)

    # KDJ
    df = calculate_kdj(df)

    # RSI
    df = calculate_rsi(df)

    # BOLL布林带
    df = calculate_boll(df)

    # ATR真实波幅
    df = calculate_atr(df)

    # 扩展指标（历史高低点、前一日数据、连续统计、K线形态、位置指标）
    df = calculate_extended_indicators(df)

    # 精度控制：对所有指标字段进行四舍五入
    # MA均线：保留2位小数
    for col in ['ma5', 'ma10', 'ma20', 'ma60']:
        if col in df.columns:
            df[col] = df[col].round(2)

    # VMA成交量均线：保留0位小数（整数）
    for col in ['vma5', 'vma10']:
        if col in df.columns:
            df[col] = df[col].round(0).astype(int)

    # MACD：保留4位小数
    for col in ['dif', 'dea', 'macd']:
        if col in df.columns:
            df[col] = df[col].round(4)

    # KDJ：保留2位小数
    for col in ['k', 'd', 'j']:
        if col in df.columns:
            df[col] = df[col].round(2)

    # RSI：保留2位小数
    for col in ['rsi6', 'rsi12', 'rsi24']:
        if col in df.columns:
            df[col] = df[col].round(2)

    # BOLL布林带：保留2位小数
    for col in ['boll_upper', 'boll_mid', 'boll_lower']:
        if col in df.columns:
            df[col] = df[col].round(2)

    # ATR真实波幅：保留2位小数
    if 'atr14' in df.columns:
        df['atr14'] = df['atr14'].round(2)

    # 涨跌幅、振幅、5日涨跌：保留2位小数
    for col in ['change_pct', 'amplitude', 'change_5d']:
        if col in df.columns:
            df[col] = df[col].round(2)

    # 扩展指标精度控制
    # 历史高低点：保留2位小数
    for col in ['max_high_5d', 'max_high_10d', 'max_high_20d', 'max_high_60d',
                'max_low_5d', 'max_low_10d', 'max_low_20d', 'max_low_60d']:
        if col in df.columns:
            df[col] = df[col].round(2)

    # 前一日数据：价格类2位小数，成交量整数，涨跌幅2位小数
    for col in ['prev_close', 'prev_high', 'prev_low', 'prev_change_pct']:
        if col in df.columns:
            df[col] = df[col].round(2)
    if 'prev_volume' in df.columns:
        df['prev_volume'] = df['prev_volume'].round(0).astype(int)

    # K线形态：body保留2位小数，比例类保留4位小数
    for col in ['body', 'upper_shadow', 'lower_shadow']:
        if col in df.columns:
            df[col] = df[col].round(2)
    for col in ['body_ratio', 'upper_shadow_ratio', 'lower_shadow_ratio']:
        if col in df.columns:
            df[col] = df[col].round(4)

    # 位置指标：保留4位小数
    for col in ['position_20d', 'position_60d']:
        if col in df.columns:
            df[col] = df[col].round(4)

    # 连续统计：整数（已在calculate_extended_indicators中处理）

    return df


def save_indicators_to_db(ts_code, df, frequency='d', save_all=False):
    """
    保存技术指标到数据库

    参数:
        ts_code: 股票代码
        df: 包含技术指标的DataFrame
        frequency: 数据周期
        save_all: 是否保存所有数据（False时只保存最后一天）

    返回:
        bool: 是否成功
    """
    try:
        from utils.db_helper import get_db_connection

        with get_db_connection() as conn:
            # 统一使用 trade_date 列（数据库表结构就是 trade_date，不是 timestamp）
            # 将各种日期列名统一为 trade_date
            df = df.copy()
            if 'trade_date' not in df.columns:
                if 'timestamp' in df.columns:
                    df['trade_date'] = df['timestamp']
                elif 'date' in df.columns:
                    df['trade_date'] = df['date']
                else:
                    # 尝试使用索引
                    if hasattr(df.index, 'name'):
                        df['trade_date'] = df.index
                    else:
                        raise ValueError("DataFrame 中找不到日期列")

            # 如果不保存全部，只取最后一条
            if not save_all and len(df) > 0:
                df = df.tail(1)

            # 保存数据
            # 注意：只保存数据库中实际存在的字段
            # 扩展字段（max_high_5d, consecutive_up_days 等）不保存到数据库
            # 因为这些字段在策略模板引擎中未被使用
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO stock_indicators
                    (ts_code, trade_date, frequency,
                     ma5, ma10, ma20, ma60,
                     vma5, vma10,
                     change_pct, change_5d,
                     dif, dea, macd,
                     k, d, j,
                     rsi6, rsi12, rsi24,
                     boll_upper, boll_mid, boll_lower,
                     atr14)
                    VALUES (?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?,
                            ?, ?,
                            ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?,
                            ?)
                """, (
                    ts_code,
                    row['trade_date'],
                    frequency,
                    row.get('ma5'), row.get('ma10'), row.get('ma20'), row.get('ma60'),
                    row.get('vma5'), row.get('vma10'),
                    row.get('change_pct'), row.get('change_5d'),
                    row.get('dif'), row.get('dea'), row.get('macd'),
                    row.get('k'), row.get('d'), row.get('j'),
                    row.get('rsi6'), row.get('rsi12'), row.get('rsi24'),
                    row.get('boll_upper'), row.get('boll_mid'), row.get('boll_lower'),
                    row.get('atr14')
                ))

            conn.commit()
            return True

    except Exception as e:
        print(f"保存指标失败: {e}")
        return False
