# -*- coding: utf-8 -*-
"""
Parquet 选股器页面与筛选逻辑
"""

from pathlib import Path

import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:
    class _StreamlitStub:
        @staticmethod
        def cache_data(show_spinner=False):
            def decorator(func):
                return func

            return decorator

        @staticmethod
        def title(*args, **kwargs):
            return None

        @staticmethod
        def info(*args, **kwargs):
            return None

    st = _StreamlitStub()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "data.parquet"

RESULT_COLUMNS = [
    "ts_code",
    "name",
    "industry",
    "close",
    "pct_chg",
    "pe_ttm",
    "pb",
    "turnover_rate",
    "vol_ratio_5",
    "net_mf_amount",
]

CUSTOM_FILTER_GROUPS = {
    "估值指标": ["pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm", "total_mv", "circ_mv"],
    "价格与涨幅": ["close", "pct_chg", "change"],
    "成交与流动性": ["vol", "amount", "turnover_rate", "turnover_rate_f", "volume_ratio", "vol_ratio_5"],
    "资金流向": [
        "net_mf_amount",
        "net_mf_vol",
        "buy_lg_amount",
        "sell_lg_amount",
        "buy_elg_amount",
        "sell_elg_amount",
    ],
    "技术指标": [
        "macd",
        "macd_dif",
        "macd_dea",
        "kdj_k",
        "kdj_d",
        "kdj_j",
        "rsi_6",
        "rsi_12",
        "rsi_24",
        "boll_upper",
        "boll_mid",
        "boll_lower",
        "cci",
    ],
}

OPERATORS = ["不筛选", ">", ">=", "<", "<=", "="]

PRESET_RULES = {
    "低估值": [
        {"field": "pe_ttm", "operator": ">", "value": 0},
        {"field": "pe_ttm", "operator": "<=", "value": 30},
        {"field": "pb", "operator": ">", "value": 0},
        {"field": "pb", "operator": "<=", "value": 3},
    ],
    "高换手": [
        {"field": "turnover_rate", "operator": ">=", "value": 3},
    ],
    "技术超卖": [
        {"field": "rsi_6", "operator": "<=", "value": 30},
    ],
    "资金净入": [
        {"field": "net_mf_amount", "operator": ">", "value": 0},
    ],
    "成长股": [
        {"field": "pct_chg", "operator": ">", "value": 0},
        {"field": "pe_ttm", "operator": ">", "value": 0},
        {"field": "ps_ttm", "operator": ">", "value": 0},
    ],
}

MOMENTUM_OPTIONS = {
    "20日新高": "break_high_20",
    "60日新高": "break_high_60",
    "120日新高": "break_high_120",
    "年内新高": "break_high_250",
    "连涨3日": "consec_up_3",
    "连涨5日": "consec_up_5",
}

PATTERN_OPTIONS = {
    "箱体突破": "pattern_box_breakout",
    "量价齐升": "pattern_vol_price_up",
    "平台突破": "pattern_platform_break",
    "三角收敛": "pattern_triangle_squeeze",
    "红三兵": "pattern_red_three",
    "均线金叉": "pattern_golden_cross",
    "老鸭头": "pattern_duck_head",
    "双底": "pattern_double_bottom",
    "圆弧底": "pattern_arc_bottom",
    "均线多头": "pattern_ma_bull",
    "首板": "pattern_first_limit",
    "连板": "pattern_multi_limit",
}

FIELD_GROUPS = {
    "基础标识": ["ts_code", "name", "industry", "area", "trade_date"],
    "估值与市值": [
        "close",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe",
        "pe_ttm",
        "pb",
        "ps",
        "ps_ttm",
        "dv_ratio",
        "dv_ttm",
        "total_share",
        "float_share",
        "free_share",
        "total_mv",
        "circ_mv",
    ],
    "价格与成交": ["open", "high", "low", "pre_close", "change", "pct_chg", "vol", "amount"],
    "资金流": [
        "buy_sm_vol",
        "buy_sm_amount",
        "sell_sm_vol",
        "sell_sm_amount",
        "buy_md_vol",
        "buy_md_amount",
        "sell_md_vol",
        "sell_md_amount",
        "buy_lg_vol",
        "buy_lg_amount",
        "sell_lg_vol",
        "sell_lg_amount",
        "buy_elg_vol",
        "buy_elg_amount",
        "sell_elg_vol",
        "sell_elg_amount",
        "net_mf_vol",
        "net_mf_amount",
    ],
    "复权价与技术指标": [
        "adj_factor",
        "open_hfq",
        "close_hfq",
        "high_hfq",
        "low_hfq",
        "open_qfq",
        "close_qfq",
        "high_qfq",
        "low_qfq",
        "pre_close_hfq",
        "pre_close_qfq",
        "macd",
        "macd_dif",
        "macd_dea",
        "kdj_k",
        "kdj_d",
        "kdj_j",
        "rsi_6",
        "rsi_12",
        "rsi_24",
        "boll_upper",
        "boll_mid",
        "boll_lower",
        "cci",
    ],
    "动量因子": [
        "break_high_20",
        "break_high_60",
        "break_high_120",
        "break_high_250",
        "consec_up_days",
        "consec_up_3",
        "consec_up_5",
        "vol_ratio_5",
    ],
    "形态信号": [
        "pattern_box_breakout",
        "pattern_vol_price_up",
        "pattern_platform_break",
        "pattern_triangle_squeeze",
        "pattern_red_three",
        "pattern_golden_cross",
        "pattern_duck_head",
        "pattern_double_bottom",
        "pattern_arc_bottom",
        "pattern_ma_bull",
        "pattern_high_tight",
        "pattern_first_limit",
        "pattern_multi_limit",
    ],
}


@st.cache_data(show_spinner=False)
def load_screener_data(file_path=None):
    """读取 parquet 选股数据"""
    target = Path(file_path) if file_path else DATA_FILE
    if not target.exists():
        raise FileNotFoundError(f"选股数据文件不存在: {target}")
    try:
        return pd.read_parquet(target)
    except Exception as exc:
        raise ValueError(f"读取选股数据失败: {exc}") from exc


def get_latest_trade_date(df):
    """返回最新交易日字符串"""
    trade_dates = df["trade_date"].astype(str).tolist()
    return max(trade_dates)


def validate_required_columns(df, required_fields):
    """校验必需字段是否存在"""
    missing_fields = [field for field in required_fields if field not in df.columns]
    if missing_fields:
        missing_text = ", ".join(missing_fields)
        raise ValueError(f"缺少必需字段: {missing_text}")


def build_filters_from_presets(selected_presets):
    """将预设按钮展开为底层规则"""
    rules = []
    for preset in selected_presets or []:
        rules.extend(PRESET_RULES.get(preset, []))
    return rules


def resolve_flag_fields(selected_labels, option_mapping):
    """将 UI 选项映射到字段名"""
    fields = []
    for label in selected_labels or []:
        if label not in option_mapping:
            raise ValueError(f"未知筛选项: {label}")
        fields.append(option_mapping[label])
    return fields


def apply_numeric_rule(df, field, operator, value):
    """执行单条数值比较规则"""
    if operator == ">":
        return df[df[field] > value]
    if operator == ">=":
        return df[df[field] >= value]
    if operator == "<":
        return df[df[field] < value]
    if operator == "<=":
        return df[df[field] <= value]
    if operator == "=":
        return df[df[field] == value]
    raise ValueError(f"不支持的运算符: {operator}")


def apply_screener_filters(
    df,
    selected_presets=None,
    selected_momentum=None,
    selected_patterns=None,
    custom_rules=None,
):
    """按 AND 组合应用所有筛选条件"""
    preset_rules = build_filters_from_presets(selected_presets)
    momentum_fields = resolve_flag_fields(selected_momentum, MOMENTUM_OPTIONS)
    pattern_fields = resolve_flag_fields(selected_patterns, PATTERN_OPTIONS)
    custom_rules = custom_rules or []

    required_fields = [rule["field"] for rule in preset_rules + custom_rules]
    required_fields.extend(momentum_fields)
    required_fields.extend(pattern_fields)
    validate_required_columns(df, required_fields)

    result = df.copy()

    for field in momentum_fields + pattern_fields:
        result = result[result[field] == 1]

    for rule in preset_rules + custom_rules:
        result = apply_numeric_rule(result, rule["field"], rule["operator"], rule["value"])

    return result


def is_flag_field(field):
    """判断字段是否属于 0/1 命中型信号"""
    return field.startswith("pattern_") or field.startswith("break_high_") or field in {
        "consec_up_3",
        "consec_up_5",
    }


def format_display_value(field, value):
    """格式化详情展示值"""
    if is_flag_field(field):
        return "命中" if int(value) == 1 else "未命中"
    return value


def find_field_group(field):
    """根据字段名找到分组"""
    for group_name, fields in FIELD_GROUPS.items():
        if field in fields:
            return group_name
    return "其他字段"


def format_stock_detail(record):
    """将单条记录按分组格式化"""
    detail = {group_name: [] for group_name in FIELD_GROUPS}
    detail["其他字段"] = []

    for field, value in record.items():
        group_name = find_field_group(field)
        detail[group_name].append(
            {
                "field": field,
                "value": value,
                "display_value": format_display_value(field, value),
            }
        )

    return {group: items for group, items in detail.items() if items}


def build_result_table(df):
    """构建结果表主字段"""
    available_columns = [column for column in RESULT_COLUMNS if column in df.columns]
    return df[available_columns].copy()


def get_stock_record(df, ts_code):
    """根据 ts_code 获取完整记录"""
    match = df[df["ts_code"] == ts_code]
    if match.empty:
        raise ValueError(f"未找到股票记录: {ts_code}")
    return match.iloc[0].to_dict()


def init_screener_state():
    """初始化页面状态"""
    st.session_state.setdefault("screener_results", None)
    st.session_state.setdefault("screener_selected_stock", None)
    st.session_state.setdefault("screener_last_error", None)


def clear_screener_filters():
    """清空筛选状态和表单值"""
    st.session_state["screener_results"] = None
    st.session_state["screener_selected_stock"] = None
    st.session_state["screener_last_error"] = None

    for label in PRESET_RULES:
        st.session_state[f"screener_preset_{label}"] = False
    for label in MOMENTUM_OPTIONS:
        st.session_state[f"screener_momentum_{label}"] = False
    for label in PATTERN_OPTIONS:
        st.session_state[f"screener_pattern_{label}"] = False
    for fields in CUSTOM_FILTER_GROUPS.values():
        for field in fields:
            st.session_state[f"screener_op_{field}"] = "不筛选"
            st.session_state[f"screener_value_{field}"] = 0.0


def collect_selected_options(option_mapping, key_prefix):
    """从 session_state 提取勾选项"""
    selected = []
    for label in option_mapping:
        if st.session_state.get(f"{key_prefix}_{label}", False):
            selected.append(label)
    return selected


def collect_custom_rules():
    """从表单状态收集自定义规则"""
    rules = []
    for fields in CUSTOM_FILTER_GROUPS.values():
        for field in fields:
            operator = st.session_state.get(f"screener_op_{field}", "不筛选")
            value = st.session_state.get(f"screener_value_{field}", 0.0)
            if operator != "不筛选":
                rules.append({"field": field, "operator": operator, "value": value})
    return rules


def render_toggle_group(title, option_mapping, key_prefix, columns_per_row=3):
    """渲染多选开关网格"""
    st.markdown(f"#### {title}")
    labels = list(option_mapping.keys())
    for start in range(0, len(labels), columns_per_row):
        columns = st.columns(columns_per_row)
        row_labels = labels[start:start + columns_per_row]
        for index, label in enumerate(row_labels):
            with columns[index]:
                st.checkbox(label, key=f"{key_prefix}_{label}")


def render_custom_filters(df):
    """渲染自定义筛选区域"""
    st.markdown("#### 自定义筛选")

    for group_name, fields in CUSTOM_FILTER_GROUPS.items():
        with st.expander(group_name, expanded=group_name in {"估值指标", "价格与涨幅", "成交与流动性"}):
            for field in fields:
                if field not in df.columns:
                    continue

                label_col, op_col, value_col = st.columns([2.2, 1.4, 1.8])
                with label_col:
                    st.caption(field)
                with op_col:
                    st.selectbox(
                        "运算符",
                        options=OPERATORS,
                        key=f"screener_op_{field}",
                        label_visibility="collapsed",
                    )
                with value_col:
                    st.number_input(
                        "值",
                        value=float(st.session_state.get(f"screener_value_{field}", 0.0)),
                        key=f"screener_value_{field}",
                        label_visibility="collapsed",
                    )


def count_selected_conditions(selected_presets, selected_momentum, selected_patterns, custom_rules):
    """统计当前已选条件数"""
    return len(selected_presets) + len(selected_momentum) + len(selected_patterns) + len(custom_rules)


def render_stock_detail(detail):
    """渲染单股完整详情"""
    st.markdown("### 股票完整字段")
    for group_name, items in detail.items():
        with st.expander(group_name, expanded=group_name in {"基础标识", "估值与市值", "价格与成交"}):
            detail_df = pd.DataFrame(
                [{"字段": item["field"], "值": item["display_value"]} for item in items]
            )
            st.dataframe(detail_df, use_container_width=True, hide_index=True)


def render_results_panel(results, latest_trade_date):
    """渲染结果面板"""
    if results is None:
        st.info("设置筛选条件后，点击“开始筛选”查看结果。")
        return

    st.markdown("### 筛选结果")

    summary_col1, summary_col2 = st.columns(2)
    with summary_col1:
        st.metric("命中数量", len(results))
    with summary_col2:
        st.metric("交易日期", latest_trade_date)

    if results.empty:
        st.warning("暂无符合条件的股票，请调整筛选条件。")
        return

    result_table = build_result_table(results)
    selector_table = result_table.copy()
    selector_table.insert(0, "更多", False)

    editor_config = None
    if hasattr(st, "column_config"):
        editor_config = {
            "更多": st.column_config.CheckboxColumn("更多", help="勾选后查看该股票的完整字段"),
        }

    edited_table = st.data_editor(
        selector_table,
        use_container_width=True,
        hide_index=True,
        disabled=[column for column in selector_table.columns if column != "更多"],
        column_config=editor_config,
        key="screener_result_editor",
    )

    selected_rows = edited_table[edited_table["更多"]]
    if not selected_rows.empty:
        selected_ts_code = selected_rows.iloc[0]["ts_code"]
        st.session_state["screener_selected_stock"] = selected_ts_code

    selected_ts_code = st.session_state.get("screener_selected_stock")
    if selected_ts_code:
        record = get_stock_record(results, selected_ts_code)
        detail = format_stock_detail(record)
        render_stock_detail(detail)


def render():
    """渲染选股器页面"""
    init_screener_state()

    st.title("🎛️ 选股器")
    st.caption("直接读取 data/data.parquet，当日截面多条件筛选。")

    try:
        df = load_screener_data()
    except (FileNotFoundError, ValueError) as exc:
        st.error(str(exc))
        return

    latest_trade_date = get_latest_trade_date(df)
    latest_df = df[df["trade_date"].astype(str) == latest_trade_date].copy()

    left_col, right_col = st.columns([1.05, 1.95], gap="large")

    with left_col:
        st.markdown("### 筛选条件")
        st.text_input("交易日期", value=latest_trade_date, disabled=True)

        with st.form("screener_filters_form"):
            st.markdown("#### 预设条件")
            preset_columns = st.columns(2)
            preset_labels = list(PRESET_RULES.keys())
            for index, label in enumerate(preset_labels):
                with preset_columns[index % 2]:
                    st.checkbox(label, key=f"screener_preset_{label}")

            render_toggle_group("动量因子快选", MOMENTUM_OPTIONS, "screener_momentum", columns_per_row=3)
            render_toggle_group("技术形态快选", PATTERN_OPTIONS, "screener_pattern", columns_per_row=3)
            render_custom_filters(latest_df)

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                start_filter = st.form_submit_button("开始筛选", use_container_width=True, type="primary")
            with action_col2:
                reset_filter = st.form_submit_button("重置", use_container_width=True)

        if reset_filter:
            clear_screener_filters()
            st.rerun()

        if start_filter:
            selected_presets = collect_selected_options(PRESET_RULES, "screener_preset")
            selected_momentum = collect_selected_options(MOMENTUM_OPTIONS, "screener_momentum")
            selected_patterns = collect_selected_options(PATTERN_OPTIONS, "screener_pattern")
            custom_rules = collect_custom_rules()

            try:
                results = apply_screener_filters(
                    latest_df,
                    selected_presets=selected_presets,
                    selected_momentum=selected_momentum,
                    selected_patterns=selected_patterns,
                    custom_rules=custom_rules,
                )
            except ValueError as exc:
                st.session_state["screener_results"] = None
                st.session_state["screener_last_error"] = str(exc)
                st.session_state["screener_selected_stock"] = None
            else:
                st.session_state["screener_results"] = results
                st.session_state["screener_last_error"] = None
                st.session_state["screener_selected_stock"] = None
                st.session_state["screener_condition_count"] = count_selected_conditions(
                    selected_presets,
                    selected_momentum,
                    selected_patterns,
                    custom_rules,
                )

        if st.session_state.get("screener_last_error"):
            st.error(st.session_state["screener_last_error"])

    with right_col:
        if st.session_state.get("screener_results") is not None:
            stats_col1, stats_col2 = st.columns(2)
            with stats_col1:
                st.metric("当前数据日期", latest_trade_date)
            with stats_col2:
                st.metric("已选条件数", st.session_state.get("screener_condition_count", 0))

        render_results_panel(st.session_state.get("screener_results"), latest_trade_date)
