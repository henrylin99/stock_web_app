# -*- coding: utf-8 -*-
"""
SQL构建工具
解析策略模板并生成参数化的SQL查询
"""

import re
import json
from utils.field_mapper import map_parameter_to_field, validate_field_name


class SQLBuilder:
    """SQL条件构建器"""

    def __init__(self):
        """初始化SQL构建器"""
        # 正则表达式模式
        self.param_pattern = r'\b([a-z_][a-z0-9_]*)\b'  # 匹配参数名或字段名

    def build_condition(self, template, params):
        """
        构建SQL条件并返回参数化查询

        参数:
            template: SQL条件模板（如 "ma_short_1 > ma_short_2 AND breakout_ratio > 1"）
            params: 参数字典（如 {"ma_short_1": 5, "ma_short_2": 10, "breakout_ratio": 2.0}）

        返回:
            tuple: (sql_condition, param_list)
                - sql_condition: 参数化的SQL条件字符串
                - param_list: 参数值列表（用于 ? 占位符）
        """
        if not template:
            return "1=1", []

        sql_parts = []
        param_list = []
        tokens = self._tokenize(template)

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # 跳过空格
            if token.isspace():
                sql_parts.append(token)
                i += 1
                continue

            # 处理SQL关键字和操作符
            if token.upper() in ('AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'LIKE', 'IS', 'NULL'):
                sql_parts.append(token.upper())
                i += 1
                continue

            # 处理操作符
            if token in ('>', '<', '>=', '<=', '=', '!=', '<>', '+', '-', '*', '/', '%', '(', ')'):
                sql_parts.append(token)
                i += 1
                continue

            # 处理数字（直接保留）
            if re.match(r'^\d+\.?\d*$', token):
                sql_parts.append(token)
                i += 1
                continue

            # ============ 优先处理特殊字段映射参数 ============

            # MA变量参数：ma_short_1, ma_short_2, ma_long_1, etc.
            # 这些参数的值需要映射为字段名（如 ma5, ma10）
            if re.match(r'^ma_(short|long)_(1|2|3)$', token):
                if token in params:
                    field = map_parameter_to_field(token, params[token])
                    sql_parts.append(field)
                    i += 1
                    continue

            # 周期参数：ma_period, vma_period, rsi_period
            # 这些参数的值需要映射为字段名（如 ma20, vma5, rsi6）
            if token in ('ma_period', 'vma_period', 'rsi_period'):
                if token in params:
                    field = map_parameter_to_field(token, params[token])
                    sql_parts.append(field)
                    i += 1
                    continue

            # 特殊：max_high 和 max_low 需要结合 lookback_days
            if token in ('max_high', 'max_low'):
                if 'lookback_days' in params:
                    mapping = map_parameter_to_field('lookback_days', params['lookback_days'])
                    field = mapping.get(token, token)
                    sql_parts.append(field)
                    i += 1
                    continue

            # ============ 处理值参数（替换为 ?） ============

            # 检查是否是值参数（需要替换为 ? 占位符）
            value_params = ('consecutive_days', 'min_rise', 'max_rise',
                           'breakout_ratio', 'drop_ratio', 'volume_ratio',
                           'price_rise', 'expand_ratio', 'limit_up_pct',
                           'oversold_level', 'low_level', 'kdj_threshold',
                           'rsi_threshold', 'touch_ratio', 'boll_k')

            if token in value_params and token in params:
                sql_parts.append('?')
                param_list.append(params[token])
                i += 1
                continue

            # ============ 处理布尔参数 ============

            # 处理参数名或字段名（通用处理）
            if token in params:
                # 这是一个参数值，需要替换为 ?
                param_value = params[token]

                # 检查是否是布尔参数
                if isinstance(param_value, bool):
                    # 布尔参数：True 保留条件，False 替换为 1=1
                    if not param_value:
                        # 找到整个条件并替换为 (1=1)
                        j = i
                        balance = 0
                        while j < len(tokens):
                            if tokens[j] == '(':
                                balance += 1
                            elif tokens[j] == ')':
                                balance -= 1
                            j += 1
                            # 简化：遇到 AND 或 OR 时停止
                            if j < len(tokens) and tokens[j].upper() in ('AND', 'OR'):
                                break
                        sql_parts.append('(1=1)')
                        i = j
                        continue
                else:
                    # 非布尔参数：替换为占位符
                    sql_parts.append('?')
                    param_list.append(param_value)
                    i += 1
                    continue

            # ============ 检查是否是直接字段 ============
            if validate_field_name(token):
                sql_parts.append(token)
                i += 1
                continue

            # 无法识别的token，保持原样（可能是常量或函数）
            sql_parts.append(token)
            i += 1

        sql_condition = ''.join(sql_parts)

        return sql_condition, param_list

    def _tokenize(self, sql_string):
        """
        将SQL字符串拆分为tokens

        参数:
            sql_string: SQL字符串

        返回:
            list: token列表
        """
        # 使用正则表达式拆分
        pattern = r'(\s+|AND|OR|NOT|IN|BETWEEN|LIKE|IS|NULL|[><=!]+\d*|\d+\.?\d*|[()+*/%,-]|"[^"]*"|\b[a-z_][a-z0-9_]*\b)'
        tokens = re.findall(pattern, sql_string, re.IGNORECASE)
        return tokens

    def get_required_fields(self, template, params):
        """
        从SQL模板中提取需要的字段列表

        参数:
            template: SQL条件模板
            params: 参数字典

        返回:
            set: 需要的字段集合
        """
        fields = set()
        tokens = self._tokenize(template)

        for token in tokens:
            token = token.strip()
            if not token or token.upper() in ('AND', 'OR', 'NOT'):
                continue

            # 尝试映射参数到字段
            if token in params:
                if token == 'lookback_days':
                    # lookback_days 可能生成 max_high_Xd 或 max_low_Xd
                    if 'max_high' in template:
                        fields.add(f"max_high_{params[token]}d")
                    if 'max_low' in template:
                        fields.add(f"max_low_{params[token]}d")
                elif token in ('ma_period', 'vma_period', 'rsi_period'):
                    field = map_parameter_to_field(token, params[token])
                    fields.add(field)
                elif re.match(r'^ma_(short|long)_(1|2|3)$', token):
                    field = map_parameter_to_field(token, params[token])
                    fields.add(field)
            elif validate_field_name(token):
                fields.add(token)

        return fields


# ============ 测试代码 ============

if __name__ == "__main__":
    print("SQL构建器测试")
    print("=" * 60)

    builder = SQLBuilder()

    # 测试用例1：直接字段比较
    template1 = "dif > dea AND (dif - dea) > 0"
    params1 = {}
    sql1, list1 = builder.build_condition(template1, params1)
    print(f"\n测试1: {template1}")
    print(f"结果: {sql1}")
    print(f"参数: {list1}")

    # 测试用例2：参数替换
    template2 = "close > max_high * (1 + breakout_ratio/100)"
    params2 = {"lookback_days": 20, "breakout_ratio": 2.0}
    sql2, list2 = builder.build_condition(template2, params2)
    print(f"\n测试2: {template2}")
    print(f"结果: {sql2}")
    print(f"参数: {list2}")

    # 测试用例3：MA参数映射
    template3 = "ma_short_1 > ma_short_2 AND ma_short_2 > ma_short_3"
    params3 = {"ma_short_1": 5, "ma_short_2": 10, "ma_short_3": 20}
    sql3, list3 = builder.build_condition(template3, params3)
    print(f"\n测试3: {template3}")
    print(f"结果: {sql3}")
    print(f"参数: {list3}")

    # 测试用例4：连续上涨
    template4 = "consecutive_up_days >= consecutive_days AND change_pct > min_rise"
    params4 = {"consecutive_days": 3, "min_rise": 1.0}
    sql4, list4 = builder.build_condition(template4, params4)
    print(f"\n测试4: {template4}")
    print(f"结果: {sql4}")
    print(f"参数: {list4}")
