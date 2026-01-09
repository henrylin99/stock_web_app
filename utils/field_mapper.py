# -*- coding: utf-8 -*-
"""
字段映射工具
将策略参数映射到数据库字段
"""

import re


# ============ 数据库字段注册表 ============

# 直接可用的字段（存在于数据库中）
DIRECT_FIELDS = {
    # stock_daily_history 表
    'close', 'open', 'high', 'low', 'volume', 'amount', 'turnover_ratio',

    # stock_indicators 表 - MA均线
    'ma5', 'ma10', 'ma20', 'ma60',

    # stock_indicators 表 - 成交量均线
    'vma5', 'vma10',

    # stock_indicators 表 - MACD
    'dif', 'dea', 'macd',

    # stock_indicators 表 - KDJ
    'k', 'd', 'j',

    # stock_indicators 表 - RSI
    'rsi6', 'rsi12', 'rsi24',

    # stock_indicators 表 - 布林带
    'boll_upper', 'boll_mid', 'boll_lower',

    # stockindicators 表 - ATR
    'atr14',

    # stock_indicators 表 - 涨跌幅
    'change_pct', 'change_5d',

    # 扩展指标 - 历史高低点
    'max_high_5d', 'max_high_10d', 'max_high_20d', 'max_high_60d',
    'max_low_5d', 'max_low_10d', 'max_low_20d', 'max_low_60d',

    # 扩展指标 - 前一日数据
    'prev_close', 'prev_high', 'prev_low', 'prev_volume', 'prev_change_pct',

    # 扩展指标 - 连续统计
    'consecutive_up_days', 'consecutive_down_days',

    # 扩展指标 - K线形态
    'body', 'body_ratio', 'upper_shadow', 'lower_shadow',
    'upper_shadow_ratio', 'lower_shadow_ratio',

    # 扩展指标 - 位置指标
    'position_20d', 'position_60d',
}


# ============ 参数到字段的映射规则 ============

def map_parameter_to_field(param_name, param_value=None):
    """
    将参数名映射到数据库字段名

    参数:
        param_name: 参数名（如 'ma_period', 'ma_short_1', 'lookback_days'）
        param_value: 参数值（如 20, 5, 10）

    返回:
        str: 数据库字段名（如 'ma20', 'ma5', 'max_high_20d'）

    异常:
        ValueError: 无法映射的参数
    """
    # 1. 检查是否是直接字段
    if param_name in DIRECT_FIELDS:
        return param_name

    # 2. MA周期参数映射
    # ma_period=20 → ma20
    if param_name == 'ma_period' and param_value is not None:
        return f'ma{int(param_value)}'

    # vma_period=5 → vma5
    if param_name == 'vma_period' and param_value is not None:
        return f'vma{int(param_value)}'

    # rsi_period=6 → rsi6
    if param_name == 'rsi_period' and param_value is not None:
        return f'rsi{int(param_value)}'

    # 3. MA变量参数映射
    # ma_short_1=5 → ma5
    # ma_short_2=10 → ma10
    # ma_short_3=20 → ma20
    # ma_long_1=60 → ma60
    # ma_long_2=120 → ma120 (不存在，需要特殊处理)
    ma_pattern = r'ma_(short|long)_(1|2|3)'
    match = re.match(ma_pattern, param_name)
    if match and param_value is not None:
        return f'ma{int(param_value)}'

    # 4. 回溯天数参数映射
    # lookback_days=20 在 max_high 上下文中 → max_high_20d
    # lookback_days=20 在 max_low 上下文中 → max_low_20d
    if param_name == 'lookback_days' and param_value is not None:
        # 返回两个可能的字段，由调用者根据上下文选择
        return {
            'max_high': f'max_high_{int(param_value)}d',
            'max_low': f'max_low_{int(param_value)}d'
        }

    # 5. 其他特殊映射
    # consecutive_days=3 → consecutive_up_days 或 consecutive_down_days
    if param_name == 'consecutive_days' and param_value is not None:
        return {
            'up': 'consecutive_up_days',
            'down': 'consecutive_down_days'
        }

    # 6. 无法识别的参数
    raise ValueError(f"无法映射参数: {param_name}")


def validate_field_name(field_name):
    """
    验证字段名是否有效（存在于数据库中）

    参数:
        field_name: 字段名

    返回:
        bool: 是否有效
    """
    return field_name in DIRECT_FIELDS


def get_all_direct_fields():
    """
    获取所有直接可用字段列表

    返回:
        list: 字段名列表
    """
    return list(DIRECT_FIELDS)


# ============ 测试代码 ============

if __name__ == "__main__":
    print("字段映射工具测试")
    print("=" * 50)

    # 测试参数映射
    test_cases = [
        ('ma_period', 20, 'ma20'),
        ('ma_short_1', 5, 'ma5'),
        ('ma_short_2', 10, 'ma10'),
        ('ma_long_1', 60, 'ma60'),
        ('rsi_period', 6, 'rsi6'),
    ]

    for param_name, param_value, expected in test_cases:
        result = map_parameter_to_field(param_name, param_value)
        status = "✅" if result == expected else "❌"
        print(f"{status} {param_name}={param_value} → {result} (期望: {expected})")

    # 测试lookback_days
    print("\nlookback_days=20 →")
    result = map_parameter_to_field('lookback_days', 20)
    print(f"  max_high: {result['max_high']}")
    print(f"  max_low: {result['max_low']}")
