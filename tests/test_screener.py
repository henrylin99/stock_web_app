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

    def test_apply_screener_filters_skips_missing_momentum_field_silently(self):
        """momentum 字段不存在于 df 时应静默跳过，不抛错"""
        df = pd.DataFrame([{"ts_code": "A", "pe_ttm": 10, "pb": 2}])
        result = screener.apply_screener_filters(
            df,
            selected_momentum=["20日新高"],  # break_high_20 不在 df 中
        )
        self.assertEqual(len(result), 1)

    def test_apply_screener_filters_skips_missing_pattern_field_silently(self):
        """pattern 字段不存在于 df 时应静默跳过，不抛错"""
        df = pd.DataFrame([{"ts_code": "A", "pe_ttm": 10, "pb": 2}])
        result = screener.apply_screener_filters(
            df,
            selected_patterns=["均线金叉"],  # pattern_golden_cross 不在 df 中
        )
        self.assertEqual(len(result), 1)

    def test_apply_screener_filters_skips_missing_custom_field_silently(self):
        """自定义规则字段不存在于 df 时应静默跳过"""
        df = pd.DataFrame([{"ts_code": "A", "pe_ttm": 10}])
        result = screener.apply_screener_filters(
            df,
            custom_rules=[{"field": "nonexistent_field", "operator": ">", "value": 0}],
        )
        self.assertEqual(len(result), 1)

    def test_apply_screener_filters_raises_for_missing_preset_field(self):
        """preset 规则引用的字段缺失时应仍抛出 ValueError"""
        df = pd.DataFrame([{"ts_code": "A"}])  # 缺少 pe_ttm / pb
        with self.assertRaises(ValueError):
            screener.apply_screener_filters(df, selected_presets=["低估值"])

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

        expected_labels = ["链接"] + [
            screener.RESULT_COLUMN_LABELS.get(col, col)
            for col in screener.RESULT_COLUMNS
        ]
        self.assertEqual(result.columns.tolist(), expected_labels)

    def test_build_result_table_skips_missing_optional_columns(self):
        """结果表缺少部分字段时不应报错"""
        df = pd.DataFrame([{"ts_code": "000001.SZ", "name": "平安银行"}])
        result = screener.build_result_table(df)
        self.assertEqual(result.columns.tolist(), ["链接", "代码", "名称"])

    def test_build_result_table_link_column_uses_10jqka_url(self):
        """链接列应生成同花顺 URL，去掉交易所后缀"""
        df = pd.DataFrame([{"ts_code": "000001.SZ", "name": "平安银行"}])
        result = screener.build_result_table(df)
        self.assertEqual(result["链接"].iloc[0], "https://stockpage.10jqka.com.cn/000001/")

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

    def test_get_result_table_height_returns_500(self):
        """结果表高度应为 500（上下布局不需要 780 的高度）"""
        self.assertEqual(screener.get_result_table_height(), 500)

    def test_app_py_contains_screener_route(self):
        """app.py 应接入选股器导航和渲染路由"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_path = os.path.join(project_root, "app.py")

        with open(app_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("🎛️ 选股器", content)
        self.assertIn("render_screener()", content)


class TestCollectActiveConditionLabels(unittest.TestCase):
    """_collect_active_condition_labels 辅助函数测试"""

    def _run_with_state(self, state_dict):
        """用 patch.dict 注入假 session_state 后调用函数"""
        import unittest.mock as mock
        with mock.patch.dict(screener.st.session_state, state_dict, clear=True):
            return screener._collect_active_condition_labels()

    def test_returns_empty_when_no_conditions_set(self):
        result = self._run_with_state({})
        self.assertEqual(result, [])

    def test_returns_preset_label_when_active(self):
        result = self._run_with_state({"screener_preset_低估值": True})
        self.assertIn("低估值", result)

    def test_returns_momentum_label_when_active(self):
        result = self._run_with_state({"screener_momentum_20日新高": True})
        self.assertIn("20日新高", result)

    def test_returns_pattern_label_when_active(self):
        result = self._run_with_state({"screener_pattern_均线金叉": True})
        self.assertIn("均线金叉", result)

    def test_returns_custom_field_label_when_operator_set(self):
        result = self._run_with_state({"screener_op_pe_ttm": ">"})
        self.assertIn("pe_ttm", result)

    def test_truncates_when_more_than_10_active(self):
        """超过10个条件时截断为前10个 + 摘要项"""
        state = {}
        # 制造超过10个激活条件：6个 momentum + 5个 pattern = 11
        for label in list(screener.MOMENTUM_OPTIONS.keys()):         # 6
            state[f"screener_momentum_{label}"] = True
        for label in list(screener.PATTERN_OPTIONS.keys())[:5]:      # 5
            state[f"screener_pattern_{label}"] = True
        result = self._run_with_state(state)
        self.assertEqual(len(result), 11)      # 10 shown + 1 summary
        self.assertIn("等", result[-1])        # 摘要项含"等"字
        self.assertIn("11", result[-1])        # 摘要项显示总数11

    def test_does_not_include_inactive_conditions(self):
        result = self._run_with_state({
            "screener_preset_低估值": False,
            "screener_op_pe_ttm": "不筛选",
        })
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
