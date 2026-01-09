# -*- coding: utf-8 -*-
"""
策略模板数据结构定义
定义策略模板、条件单元、参数等数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class ConditionParam:
    """
    条件参数定义

    属性:
        name: 参数名（如 'volume_ratio'）
        label: 参数显示标签（如 '放量倍数'）
        param_type: 参数类型 ('int', 'float', 'bool')
        default_value: 默认值
        min_value: 最小值（可选）
        max_value: 最大值（可选）
        step_value: 步长（可选）
        description: 参数说明（可选）
    """
    name: str
    label: str
    param_type: str  # 'int', 'float', 'bool'
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step_value: Optional[float] = None
    description: Optional[str] = None


@dataclass
class ConditionMapping:
    """
    字段映射定义
    用于将用户参数映射到数据库字段名

    示例:
        name = "ma1_field"
        expression = "ma#{ma1_period}"
        当 ma1_period=5 时，映射结果为 "ma5"
    """
    name: str
    expression: str


@dataclass
class ConditionUnit:
    """
    条件单元定义

    策略中最小的可配置单元，对应一个SQL片段

    属性:
        id: 条件ID（如 'cond_ma5_gt_ma10'）
        label: 条件显示标签（如 'MA5 > MA10'）
        sql_template: SQL模板（如 'ma5 > ma10' 或 'volume > vma5 * #{volume_ratio}'）
        enabled: 是否默认启用
        required: 是否必需（必需条件无法取消选择）
        sort_order: 显示排序
        params: 参数列表
        mappings: 字段映射字典
    """
    id: str
    label: str
    sql_template: str
    enabled: bool = True
    required: bool = False
    sort_order: int = 0
    params: List[ConditionParam] = field(default_factory=list)
    mappings: Dict[str, str] = field(default_factory=dict)


@dataclass
class StrategyTemplate:
    """
    策略模板定义

    属性:
        id: 策略ID（如 'ma_bullish_alignment'）
        name: 策略名称（如 '均线多头排列'）
        category: 策略分类（如 '趋势型策略'）
        risk_level: 风险等级（如 '中'）
        description: 策略描述
        conditions: 条件单元列表
        combine_logic: 条件组合逻辑 ('AND' 或 'OR')
    """
    id: str
    name: str
    category: str
    risk_level: str
    description: str
    conditions: List[ConditionUnit] = field(default_factory=list)
    combine_logic: str = 'AND'
