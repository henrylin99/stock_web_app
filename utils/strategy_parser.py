# -*- coding: utf-8 -*-
"""
策略XML解析器
解析 strategies.xml 文件并转换为 StrategyTemplate 对象
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict
from utils.strategy_models import StrategyTemplate, ConditionUnit, ConditionParam


class StrategyParser:
    """
    策略XML解析器

    职责:
    - 解析 XML 文件为 StrategyTemplate 对象
    - 实现策略缓存机制
    """

    def __init__(self, xml_path: str = None):
        """
        初始化解析器

        参数:
            xml_path: XML文件路径，默认为 templates/strategies.xml
        """
        if xml_path is None:
            xml_path = Path(__file__).parent.parent / 'templates' / 'strategies.xml'
        self.xml_path = Path(xml_path)
        self._cache = {}  # 策略缓存 {strategy_id: StrategyTemplate}

    def parse_strategy(self, strategy_id: str) -> StrategyTemplate:
        """
        解析单个策略

        参数:
            strategy_id: 策略ID

        返回:
            StrategyTemplate对象

        异常:
            ValueError: 策略不存在
            ET.ParseError: XML解析错误
        """
        # 检查缓存
        if strategy_id in self._cache:
            return self._cache[strategy_id]

        # 解析XML
        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()

            # 查找策略节点
            strategy_elem = root.find(f".//strategy[@id='{strategy_id}']")
            if strategy_elem is None:
                available_ids = [s.get('id') for s in root.findall('.//strategy')]
                raise ValueError(
                    f"策略不存在: {strategy_id}\n"
                    f"可用策略ID: {', '.join(available_ids)}"
                )

            # 构建策略对象
            strategy = self._parse_strategy_element(strategy_elem)

            # 缓存
            self._cache[strategy_id] = strategy
            return strategy

        except ET.ParseError as e:
            raise ValueError(f"XML解析失败: {e}")

    def parse_all_strategies(self) -> Dict[str, StrategyTemplate]:
        """
        解析所有策略

        返回:
            {strategy_id: StrategyTemplate} 字典
        """
        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()

            strategies = {}
            for strategy_elem in root.findall('strategy'):
                strategy = self._parse_strategy_element(strategy_elem)
                strategies[strategy.id] = strategy

            return strategies

        except ET.ParseError as e:
            raise ValueError(f"XML解析失败: {e}")

    def _parse_strategy_element(self, elem: ET.Element) -> StrategyTemplate:
        """
        解析策略元素

        参数:
            elem: XML元素

        返回:
            StrategyTemplate对象
        """
        strategy_id = elem.get('id')
        name = elem.get('name')
        category = elem.get('category')
        risk_level = elem.get('risk')
        description = elem.get('description', '')

        # 解析条件单元
        conditions = []
        for cond_elem in elem.findall('condition'):
            condition = self._parse_condition_element(cond_elem)
            conditions.append(condition)

        # 按sort_order排序
        conditions.sort(key=lambda c: c.sort_order)

        # 组合逻辑
        combine_logic_elem = elem.find('combineLogic')
        if combine_logic_elem is not None and combine_logic_elem.text:
            combine_logic = combine_logic_elem.text.strip().upper()
        else:
            combine_logic = 'AND'

        return StrategyTemplate(
            id=strategy_id,
            name=name,
            category=category,
            risk_level=risk_level,
            description=description,
            conditions=conditions,
            combine_logic=combine_logic
        )

    def _parse_condition_element(self, elem: ET.Element) -> ConditionUnit:
        """
        解析条件单元元素

        参数:
            elem: XML元素

        返回:
            ConditionUnit对象
        """
        cond_id = elem.get('id')
        label = elem.get('label')
        enabled = elem.get('enabled', 'true').lower() == 'true'
        required = elem.get('required', 'false').lower() == 'true'
        sort_order = int(elem.get('sort_order', '0'))

        # SQL模板
        sql_elem = elem.find('sql')
        if sql_elem is not None and sql_elem.text:
            sql_template = sql_elem.text.strip()
        else:
            sql_template = ''

        # 解析参数
        params = []
        params_elem = elem.find('params')
        if params_elem is not None:
            for param_elem in params_elem.findall('param'):
                param = ConditionParam(
                    name=param_elem.get('name'),
                    label=param_elem.get('label'),
                    param_type=param_elem.get('type'),
                    default_value=self._parse_value(param_elem.get('default')),
                    min_value=self._parse_value(param_elem.get('min')),
                    max_value=self._parse_value(param_elem.get('max')),
                    step_value=self._parse_value(param_elem.get('step')),
                    description=param_elem.get('description')
                )
                params.append(param)

        # 解析映射
        mappings = {}
        mappings_elem = elem.find('mappings')
        if mappings_elem is not None:
            for mapping_elem in mappings_elem.findall('mapping'):
                name = mapping_elem.get('name')
                expression = mapping_elem.get('expression')
                if name and expression:
                    mappings[name] = expression

        return ConditionUnit(
            id=cond_id,
            label=label,
            sql_template=sql_template,
            enabled=enabled,
            required=required,
            sort_order=sort_order,
            params=params,
            mappings=mappings
        )

    def _parse_value(self, value_str: str) -> any:
        """
        解析值字符串为实际类型

        参数:
            value_str: 值字符串

        返回:
            解析后的值（int, float, bool, 或 str）
        """
        if value_str is None:
            return None

        value_str = value_str.strip()

        # 尝试解析为数字
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass

        # 尝试解析为布尔
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False

        # 返回字符串
        return value_str

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()

    def get_available_strategy_ids(self) -> list:
        """
        获取所有可用的策略ID列表

        返回:
            策略ID列表
        """
        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            return [s.get('id') for s in root.findall('.//strategy')]
        except:
            return []
