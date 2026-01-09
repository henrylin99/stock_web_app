# -*- coding: utf-8 -*-
"""
SQL模板渲染器
根据用户配置渲染策略模板为SQL WHERE子句
"""

import re
from typing import Tuple, List, Dict, Any
from utils.strategy_models import StrategyTemplate


class SqlTemplateRenderer:
    """
    SQL模板渲染器

    职责:
    - 根据用户选择的条件渲染SQL
    - 替换参数占位符为SQLite占位符(?)
    - 返回 (where_clause, params)
    """

    def __init__(self):
        """初始化渲染器"""
        # 匹配 #{variable} 占位符
        self.placeholder_pattern = re.compile(r'#\{(\w+)\}')

    def render(self, strategy: StrategyTemplate,
               user_config: Dict[str, Any]) -> Tuple[str, List]:
        """
        渲染策略为SQL WHERE子句

        参数:
            strategy: 策略模板对象
            user_config: 用户配置 {
                'selected_conditions': ['cond1', 'cond2'],
                'params': {'volume_ratio': 2.0, ...}
            }

        返回:
            (where_clause, params): WHERE子句和参数列表
        """
        selected = set(user_config.get('selected_conditions', []))
        user_params = user_config.get('params', {})

        conditions = []
        all_params = []

        for cond in strategy.conditions:
            # 必需条件或用户选择的条件
            if cond.required or cond.id in selected:
                cond_sql, cond_params = self._render_condition(cond, user_params)
                if cond_sql:
                    conditions.append(f"({cond_sql})")
                    all_params.extend(cond_params)

        # 如果没有任何条件，返回 1=1
        if not conditions:
            return "1=1", []

        # 组合条件
        where_clause = f" {strategy.combine_logic} ".join(conditions)
        return where_clause, all_params

    def _render_condition(self, condition,
                         user_params: Dict) -> Tuple[str, List]:
        """
        渲染单个条件

        参数:
            condition: 条件单元对象
            user_params: 用户参数值字典

        返回:
            (sql, params): SQL片段和参数列表
        """
        sql = condition.sql_template
        params = []

        # 先计算字段映射值
        mapping_values = {}
        if condition.mappings:
            for name, expression in condition.mappings.items():
                mapping_values[name] = self._eval_mapping_expression(
                    expression,
                    user_params
                )

        # 替换占位符
        def replace_placeholder(match):
            var_name = match.group(1)

            # 优先检查字段映射
            if var_name in mapping_values:
                return mapping_values[var_name]

            # 检查是否是用户参数
            if var_name in user_params:
                params.append(user_params[var_name])
                return '?'  # SQLite占位符

            # 未找到变量，保持原样（可能是直接字段名）
            return var_name

        sql = self.placeholder_pattern.sub(replace_placeholder, sql)
        return sql, params

    def _eval_mapping_expression(self, expression: str,
                                  params: Dict) -> str:
        """
        执行映射表达式

        例如: "ma#{ma1_period}" + {"ma1_period": 5} -> "ma5"

        参数:
            expression: 映射表达式
            params: 参数值字典

        返回:
            计算结果字符串
        """
        result = expression

        # 递归替换 #{var} 占位符
        while True:
            match = self.placeholder_pattern.search(result)
            if not match:
                break

            var_name = match.group(1)
            if var_name in params:
                value = str(params[var_name])
                result = result[:match.start()] + value + result[match.end():]
            else:
                # 变量未定义，保持原样
                break

        return result

    def get_required_fields(self, strategy: StrategyTemplate,
                           user_config: Dict) -> List[str]:
        """
        获取策略需要的数据库字段列表

        用于优化SQL SELECT子句，只查询必要的字段

        参数:
            strategy: 策略模板
            user_config: 用户配置

        返回:
            字段名列表
        """
        fields = set()
        selected = set(user_config.get('selected_conditions', []))

        for condition in strategy.conditions:
            if condition.required or condition.id in selected:
                # 从SQL模板中提取字段名
                condition_fields = self._extract_fields_from_sql(
                    condition.sql_template,
                    condition.mappings,
                    user_config.get('params', {})
                )
                fields.update(condition_fields)

        return list(fields)

    def _extract_fields_from_sql(self, sql: str, mappings: Dict,
                                  params: Dict) -> List[str]:
        """
        从SQL中提取字段名

        参数:
            sql: SQL模板
            mappings: 字段映射
            params: 参数值

        返回:
            字段名列表
        """
        fields = []

        # 计算映射值
        mapping_values = {}
        for name, expr in mappings.items():
            mapping_values[name] = self._eval_mapping_expression(expr, params)

        # 提取所有 #{var} 中的变量
        for match in self.placeholder_pattern.finditer(sql):
            var_name = match.group(1)

            if var_name in mapping_values:
                # 这是一个字段映射
                fields.append(mapping_values[var_name])
            elif var_name not in params:
                # 不是用户参数，可能是字段名
                fields.append(var_name)

        return fields
