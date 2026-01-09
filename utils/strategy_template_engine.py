# -*- coding: utf-8 -*-
"""
策略模板引擎
主入口，整合解析器和渲染器，提供统一的API
"""

from typing import Dict, List, Any
from utils.strategy_parser import StrategyParser
from utils.sql_template_renderer import SqlTemplateRenderer
from utils.strategy_models import StrategyTemplate


class StrategyTemplateEngine:
    """
    策略模板引擎 - 类似MyBatis的SqlSession

    职责:
    - 加载和管理策略模板
    - 根据用户配置生成SQL
    - 提供UI配置信息
    """

    def __init__(self, xml_path: str = None):
        """
        初始化引擎

        参数:
            xml_path: XML文件路径，默认为 templates/strategies.xml
        """
        self.parser = StrategyParser(xml_path)
        self.renderer = SqlTemplateRenderer()
        self._strategy_cache = {}  # 策略缓存

    # ============ 策略加载 ============

    def load_strategy(self, strategy_id: str) -> StrategyTemplate:
        """
        加载策略定义

        参数:
            strategy_id: 策略ID

        返回:
            StrategyTemplate对象
        """
        if strategy_id not in self._strategy_cache:
            self._strategy_cache[strategy_id] = self.parser.parse_strategy(strategy_id)

        return self._strategy_cache[strategy_id]

    def load_all_strategies(self) -> Dict[str, StrategyTemplate]:
        """
        加载所有策略

        返回:
            {strategy_id: StrategyTemplate} 字典
        """
        return self.parser.parse_all_strategies()

    def get_strategy_categories(self) -> Dict[str, List[StrategyTemplate]]:
        """
        获取按分类组织的策略列表

        返回:
            {category_name: [StrategyTemplate]} 字典
        """
        strategies = self.load_all_strategies()
        categories = {}

        for strategy in strategies.values():
            if strategy.category not in categories:
                categories[strategy.category] = []
            categories[strategy.category].append(strategy)

        return categories

    def get_available_strategy_ids(self) -> List[str]:
        """
        获取所有可用的策略ID列表

        返回:
            策略ID列表
        """
        return self.parser.get_available_strategy_ids()

    # ============ SQL生成 ============

    def build_sql(self, strategy_id: str,
                  user_config: Dict[str, Any]) -> tuple:
        """
        根据用户配置构建SQL

        参数:
            strategy_id: 策略ID
            user_config: 用户配置 {
                'selected_conditions': ['cond1', 'cond2'],
                'params': {'ma1_period': 5, 'volume_ratio': 2.0, ...}
            }

        返回:
            (where_clause, params): WHERE子句和参数列表
        """
        strategy = self.load_strategy(strategy_id)
        return self.renderer.render(strategy, user_config)

    def get_required_fields(self, strategy_id: str,
                           user_config: Dict) -> List[str]:
        """
        获取策略需要的数据库字段

        参数:
            strategy_id: 策略ID
            user_config: 用户配置

        返回:
            字段名列表
        """
        strategy = self.load_strategy(strategy_id)
        return self.renderer.get_required_fields(strategy, user_config)

    # ============ UI配置 ============

    def get_strategy_ui_config(self, strategy_id: str) -> Dict[str, Any]:
        """
        获取策略的UI配置信息

        返回:
            {
                'id': 'ma_bullish_alignment',
                'name': '均线多头排列',
                'category': '趋势型策略',
                'risk_level': '中',
                'description': '...',
                'combine_logic': 'AND',
                'conditions': [
                    {
                        'id': 'cond_ma5_gt_ma10',
                        'label': 'MA5 > MA10',
                        'enabled': True,
                        'required': False,
                        'sort_order': 1,
                        'params': []
                    }
                ]
            }
        """
        strategy = self.load_strategy(strategy_id)

        config = {
            'id': strategy.id,
            'name': strategy.name,
            'category': strategy.category,
            'risk_level': strategy.risk_level,
            'description': strategy.description,
            'combine_logic': strategy.combine_logic,
            'conditions': []
        }

        for condition in strategy.conditions:
            cond_config = {
                'id': condition.id,
                'label': condition.label,
                'enabled': condition.enabled,
                'required': condition.required,
                'sort_order': condition.sort_order,
                'params': []
            }

            if condition.params:
                for param in condition.params:
                    param_config = {
                        'name': param.name,
                        'label': param.label,
                        'type': param.param_type,
                        'default': param.default_value,
                        'min': param.min_value,
                        'max': param.max_value,
                        'step': param.step_value,
                        'description': param.description
                    }
                    cond_config['params'].append(param_config)

            config['conditions'].append(cond_config)

        return config

    def get_all_strategies_ui_config(self) -> Dict[str, List[Dict]]:
        """
        获取所有策略的UI配置信息（按分类组织）

        返回:
            {
                '趋势型策略': [
                    {'id': 'ma_bullish_alignment', 'name': '均线多头排列', ...},
                    ...
                ],
                '突破型策略': [...],
                '震荡型策略': [...]
            }
        """
        categories = self.get_strategy_categories()
        result = {}

        for category, strategies in categories.items():
            result[category] = []
            for strategy in strategies:
                config = {
                    'id': strategy.id,
                    'name': strategy.name,
                    'risk_level': strategy.risk_level,
                    'description': strategy.description
                }
                result[category].append(config)

        return result

    # ============ 缓存管理 ============

    def clear_cache(self):
        """清除所有缓存"""
        self._strategy_cache.clear()
        self.parser.clear_cache()

    def preload_strategies(self, strategy_ids: List[str] = None):
        """
        预加载策略到缓存

        参数:
            strategy_ids: 要预加载的策略ID列表，None表示全部
        """
        if strategy_ids is None:
            self.load_all_strategies()
        else:
            for strategy_id in strategy_ids:
                self.load_strategy(strategy_id)
