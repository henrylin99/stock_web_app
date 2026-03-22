# -*- coding: utf-8 -*-
"""
选股器模块单元测试
"""

import os
import sys
import unittest

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import screener


class TestScreenerHelpers(unittest.TestCase):
    """选股器核心纯函数测试"""

    def test_get_latest_trade_date(self):
        """应返回最新交易日"""
        df = pd.DataFrame({"trade_date": ["20260317", "20260318", "20260316"]})
        self.assertEqual(screener.get_latest_trade_date(df), "20260318")

    def test_build_filters_from_presets_low_valuation(self):
        """低估值预设应展开为四条数值规则"""
        rules = screener.build_filters_from_presets(["低估值"])
        expected = [
            {"field": "pe_ttm", "operator": ">", "value": 0},
            {"field": "pe_ttm", "operator": "<=", "value": 30},
            {"field": "pb", "operator": ">", "value": 0},
            {"field": "pb", "operator": "<=", "value": 3},
        ]
        self.assertEqual(rules, expected)

    def test_apply_screener_filters_uses_and_semantics(self):
        """预设、快选和自定义规则应按 AND 组合"""
        df = pd.DataFrame(
            [
                {
                    "ts_code": "A",
                    "pe_ttm": 10,
                    "pb": 2,
                    "turnover_rate": 5,
                    "pct_chg": 3,
                    "break_high_20": 1,
                    # 有些 parquet 落盘会把 0/1 写成字符串
                    "pattern_golden_cross": "1",
                },
                {
                    "ts_code": "B",
                    "pe_ttm": 10,
                    "pb": 2,
                    "turnover_rate": 5,
                    "pct_chg": 3,
                    "break_high_20": 1,
                    "pattern_golden_cross": "0",
                },
                {
                    "ts_code": "C",
                    "pe_ttm": 50,
                    "pb": 2,
                    "turnover_rate": 5,
                    "pct_chg": 3,
                    "break_high_20": 1,
                    "pattern_golden_cross": "1",
                },
            ]
        )

        result = screener.apply_screener_filters(
            df,
            selected_presets=["低估值", "高换手"],
            selected_momentum=["20日新高"],
            selected_patterns=["均线金叉"],
            custom_rules=[{"field": "pct_chg", "operator": ">", "value": 1}],
        )

        self.assertEqual(result["ts_code"].tolist(), ["A"])

    def test_validate_required_columns_raises_clear_error(self):
        """字段缺失时应抛出清晰错误"""
        df = pd.DataFrame([{"ts_code": "000001.SZ"}])

        with self.assertRaises(ValueError) as ctx:
            screener.validate_required_columns(df, ["ts_code", "trade_date", "name"])

        self.assertIn("trade_date", str(ctx.exception))
        self.assertIn("name", str(ctx.exception))

    def test_format_stock_detail_groups_all_fields_and_formats_flags(self):
        """详情格式化应覆盖全部字段并转换 flag 展示值"""
        record = {
            "ts_code": "000001.SZ",
            "name": "平安银行",
            "trade_date": "20260317",
            "pe_ttm": 5.2,
            "break_high_20": 1,
            "pattern_golden_cross": 0,
        }

        field_meta = {
            "ts_code": {"cn_name": "股票代码", "cn_desc": "Tushare 标准代码"},
            "break_high_20": {"cn_name": "突破20日新高", "cn_desc": "今日最高价是否突破近 20 日最高"},
        }
        detail = screener.format_stock_detail(record, field_meta=field_meta)

        all_fields = {item["field"] for items in detail.values() for item in items}
        self.assertEqual(all_fields, set(record.keys()))

        momentum_items = {
            item["field"]: item["display_value"]
            for item in detail["动量因子"]
        }
        pattern_items = {
            item["field"]: item["display_value"]
            for item in detail["形态信号"]
        }
        self.assertEqual(momentum_items["break_high_20"], "命中")
        self.assertEqual(pattern_items["pattern_golden_cross"], "未命中")

        ts_code_row = [item for item in detail["基础标识"] if item["field"] == "ts_code"][0]
        self.assertEqual(ts_code_row["cn_name"], "股票代码")
        self.assertEqual(ts_code_row["cn_desc"], "Tushare 标准代码")

    def test_parse_field_dictionary_markdown_extracts_cn_name_and_desc(self):
        """应能从数据字典 markdown 解析出字段中文名和中文说明"""
        markdown_text = (
            "| 字段 | 中文说明 | English Description | 类型 | 样例值 | 观察 |\n"
            "|---|---|---|---|---|---|\n"
            "| `ts_code` | 股票代码（Tushare 标准） | Security code | `str` | `000001.SZ` | x |\n"
            "| `pe_ttm` | 滚动市盈率 TTM | Trailing P/E | `float64` | `4.9` | x |\n"
            "\n"
            "| 字段 | 中文口径 | English |\n"
            "|---|---|---|\n"
            "| `break_high_20/60` | 今日最高价是否大于对应窗口前 N 日最高价 | ... |\n"
        )

        meta = screener.parse_field_dictionary_markdown(markdown_text)

        self.assertEqual(meta["ts_code"]["cn_name"], "股票代码（Tushare 标准）")
        self.assertEqual(meta["ts_code"]["cn_desc"], "")
        self.assertEqual(meta["break_high_20"]["cn_desc"], "今日最高价是否大于对应窗口前 N 日最高价")
        self.assertEqual(meta["break_high_60"]["cn_desc"], "今日最高价是否大于对应窗口前 N 日最高价")


class TestScreenerPresentation(unittest.TestCase):
    """选股器结果整形测试"""

    def test_build_result_table_uses_main_columns(self):
        """结果表应保留主要字段顺序"""
        df = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "name": "平安银行",
                    "industry": "银行",
                    "close": 11.03,
                    "pct_chg": 1.0,
                    "pe_ttm": 4.9,
                    "pb": 0.48,
                    "turnover_rate": 0.55,
                    "vol_ratio_5": 1.4,
                    "net_mf_amount": 28892.55,
                    "extra": 1,
                }
            ]
        )

        result = screener.build_result_table(df)

        self.assertEqual(result.columns.tolist(), screener.RESULT_COLUMNS)

    def test_build_result_table_skips_missing_optional_columns(self):
        """结果表缺少部分字段时不应报错"""
        df = pd.DataFrame([{"ts_code": "000001.SZ", "name": "平安银行"}])
        result = screener.build_result_table(df)
        self.assertEqual(result.columns.tolist(), ["ts_code", "name"])

    def test_get_stock_record_resolves_full_row_by_ts_code(self):
        """应能通过 ts_code 找到完整记录"""
        df = pd.DataFrame(
            [
                {"ts_code": "000001.SZ", "name": "平安银行", "close": 11.03},
                {"ts_code": "000002.SZ", "name": "万科A", "close": 9.88},
            ]
        )

        record = screener.get_stock_record(df, "000002.SZ")

        self.assertEqual(record["name"], "万科A")
        self.assertEqual(record["close"], 9.88)

    def test_apply_screener_filters_returns_all_rows_when_no_filters_selected(self):
        """没有任何条件时应返回全量结果"""
        df = pd.DataFrame(
            [
                {"ts_code": "000001.SZ", "name": "平安银行"},
                {"ts_code": "000002.SZ", "name": "万科A"},
            ]
        )

        result = screener.apply_screener_filters(df)

        self.assertEqual(result["ts_code"].tolist(), ["000001.SZ", "000002.SZ"])

    def test_get_result_table_height_uses_fixed_tall_layout(self):
        """结果表高度应使用较高固定值，接近左栏高度"""
        self.assertGreaterEqual(screener.get_result_table_height(), 720)

    def test_app_py_contains_screener_route(self):
        """app.py 应接入选股器导航和渲染路由"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_path = os.path.join(project_root, "app.py")

        with open(app_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("🎛️ 选股器", content)
        self.assertIn("render_screener()", content)


if __name__ == "__main__":
    unittest.main()
