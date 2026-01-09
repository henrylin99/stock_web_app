# -*- coding: utf-8 -*-
"""
策略模板引擎单元测试
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.strategy_template_engine import StrategyTemplateEngine


class TestStrategyTemplateEngine(unittest.TestCase):
    """策略模板引擎测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.engine = StrategyTemplateEngine()

    def test_load_strategy(self):
        """测试加载策略"""
        strategy = self.engine.load_strategy('ma_bullish_alignment')
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.id, 'ma_bullish_alignment')
        self.assertEqual(strategy.name, '均线多头排列')
        self.assertEqual(strategy.category, '趋势型策略')
        self.assertEqual(strategy.risk_level, '中')
        self.assertEqual(len(strategy.conditions), 4)

    def test_load_all_strategies(self):
        """测试加载所有策略"""
        strategies = self.engine.load_all_strategies()
        self.assertIsInstance(strategies, dict)
        self.assertGreaterEqual(len(strategies), 9)

        # 检查包含的策略
        self.assertIn('ma_bullish_alignment', strategies)
        self.assertIn('macd_golden_cross', strategies)
        self.assertIn('volume_breakout', strategies)
        self.assertIn('kdj_oversold_golden_cross', strategies)

    def test_get_strategy_categories(self):
        """测试获取策略分类"""
        categories = self.engine.get_strategy_categories()
        self.assertIsInstance(categories, dict)

        # 应该有三个分类
        self.assertIn('趋势型策略', categories)
        self.assertIn('突破型策略', categories)
        self.assertIn('震荡型策略', categories)

    def test_build_sql_all_conditions(self):
        """测试生成SQL - 选择所有条件"""
        user_config = {
            'selected_conditions': [
                'cond_ma5_gt_ma10',
                'cond_ma10_gt_ma20',
                'cond_ma20_gt_ma60'
            ],
            'params': {}
        }

        where_clause, params = self.engine.build_sql('ma_bullish_alignment', user_config)

        # 验证SQL包含所有选择的条件
        self.assertIn('ma5 > ma10', where_clause)
        self.assertIn('ma10 > ma20', where_clause)
        self.assertIn('ma20 > ma60', where_clause)
        self.assertEqual(where_clause.count('AND'), 2)

    def test_build_sql_partial_conditions(self):
        """测试生成SQL - 只选择部分条件"""
        user_config = {
            'selected_conditions': ['cond_ma5_gt_ma10'],  # 只选1个条件
            'params': {}
        }

        where_clause, params = self.engine.build_sql('ma_bullish_alignment', user_config)

        # 应该只包含选择的条件
        self.assertIn('ma5 > ma10', where_clause)
        self.assertNotIn('ma10 > ma20', where_clause)
        self.assertNotIn('ma20 > ma60', where_clause)

    def test_build_sql_with_params(self):
        """测试生成SQL - 带参数的条件"""
        user_config = {
            'selected_conditions': ['cond_volume_expand', 'cond_price_rise'],
            'params': {
                'volume_ratio': 2.5,
                'price_rise': 5.0
            }
        }

        where_clause, params = self.engine.build_sql('volume_breakout', user_config)

        # 验证参数化查询
        self.assertIn('volume > vma5 * ?', where_clause)
        self.assertIn('change_pct > ?', where_clause)
        self.assertEqual(len(params), 2)
        self.assertIn(2.5, params)
        self.assertIn(5.0, params)

    def test_build_sql_required_condition(self):
        """测试必需条件（即使用户未选择也必须包含）"""
        user_config = {
            'selected_conditions': [],  # 用户未选择任何条件
            'params': {}
        }

        where_clause, params = self.engine.build_sql('macd_golden_cross', user_config)

        # cond_dif_gt_dea 是必需条件，应该自动包含
        self.assertIn('dif > dea', where_clause)

    def test_get_strategy_ui_config(self):
        """测试获取策略UI配置"""
        config = self.engine.get_strategy_ui_config('ma_bullish_alignment')

        self.assertEqual(config['id'], 'ma_bullish_alignment')
        self.assertEqual(config['name'], '均线多头排列')
        self.assertEqual(config['category'], '趋势型策略')
        self.assertEqual(len(config['conditions']), 4)

        # 检查第一个条件
        cond1 = config['conditions'][0]
        self.assertEqual(cond1['id'], 'cond_ma5_gt_ma10')
        self.assertEqual(cond1['label'], 'MA5 > MA10')
        self.assertTrue(cond1['enabled'])
        self.assertFalse(cond1['required'])

    def test_get_strategy_ui_config_with_params(self):
        """测试获取带参数的策略UI配置"""
        config = self.engine.get_strategy_ui_config('volume_breakout')

        # volume_breakout 有两个条件，每个都有参数
        self.assertEqual(len(config['conditions']), 2)

        # 第一个条件有参数
        cond1 = config['conditions'][0]
        self.assertEqual(cond1['id'], 'cond_volume_expand')
        self.assertEqual(len(cond1['params']), 1)

        param = cond1['params'][0]
        self.assertEqual(param['name'], 'volume_ratio')
        self.assertEqual(param['label'], '放量倍数')
        self.assertEqual(param['type'], 'float')
        self.assertEqual(param['default'], 2.0)
        self.assertEqual(param['min'], 1.5)
        self.assertEqual(param['max'], 5.0)

    def test_get_all_strategies_ui_config(self):
        """测试获取所有策略UI配置"""
        config = self.engine.get_all_strategies_ui_config()

        # 验证分类结构
        self.assertIn('趋势型策略', config)
        self.assertIn('突破型策略', config)
        self.assertIn('震荡型策略', config)

        # 每个分类至少有1个策略
        self.assertGreater(len(config['趋势型策略']), 0)
        self.assertGreater(len(config['突破型策略']), 0)
        self.assertGreater(len(config['震荡型策略']), 0)

    def test_clear_cache(self):
        """测试清除缓存"""
        # 先加载一个策略（会被缓存）
        self.engine.load_strategy('ma_bullish_alignment')

        # 清除缓存
        self.engine.clear_cache()

        # 重新加载应该仍然能工作
        strategy = self.engine.load_strategy('ma_bullish_alignment')
        self.assertIsNotNone(strategy)

    def test_preload_strategies(self):
        """测试预加载策略"""
        # 预加载所有策略
        self.engine.preload_strategies()

        # 验证缓存已填充
        strategies = self.engine.load_all_strategies()
        self.assertGreaterEqual(len(strategies), 9)


class TestSQLRendering(unittest.TestCase):
    """SQL渲染测试"""

    def setUp(self):
        """每个测试前的设置"""
        self.engine = StrategyTemplateEngine()

    def test_render_simple_condition(self):
        """测试渲染简单条件（无参数）"""
        user_config = {
            'selected_conditions': ['cond_dif_gt_dea'],
            'params': {}
        }

        where_clause, params = self.engine.build_sql('macd_golden_cross', user_config)

        self.assertEqual(where_clause, '(dif > dea)')
        self.assertEqual(len(params), 0)

    def test_render_complex_condition(self):
        """测试渲染复杂条件（有参数）"""
        user_config = {
            'selected_conditions': ['cond_volume_expand'],
            'params': {'volume_ratio': 3.0}
        }

        where_clause, params = self.engine.build_sql('volume_breakout', user_config)

        self.assertIn('volume > vma5 * ?', where_clause)
        self.assertEqual(params, [3.0])

    def test_render_multiple_conditions(self):
        """测试渲染多个条件组合"""
        user_config = {
            'selected_conditions': [
                'cond_volume_expand',
                'cond_price_rise'
            ],
            'params': {
                'volume_ratio': 2.0,
                'price_rise': 4.0
            }
        }

        where_clause, params = self.engine.build_sql('volume_breakout', user_config)

        # 验证AND连接
        self.assertIn('AND', where_clause)
        self.assertEqual(len(params), 2)

    def test_render_empty_selection(self):
        """测试空选择（用户未选择任何可选条件）"""
        user_config = {
            'selected_conditions': [],
            'params': {}
        }

        where_clause, params = self.engine.build_sql('ma_bullish_alignment', user_config)

        # 应该返回1=1（没有必需条件）
        self.assertEqual(where_clause, '1=1')
        self.assertEqual(len(params), 0)


if __name__ == '__main__':
    unittest.main()
