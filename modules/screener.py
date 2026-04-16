# -*- coding: utf-8 -*-
"""
Parquet 选股器页面与筛选逻辑
"""

from pathlib import Path

import pandas as pd
import re

import config

try:
    import streamlit as st
except ModuleNotFoundError:
    class _SessionStateStub(dict):
        """Minimal session_state stub that supports dict and attribute access."""
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(key)

        def __setattr__(self, key, value):
            self[key] = value

        def get(self, key, default=None):
            return super().get(key, default)

    class _StreamlitStub:
        session_state = _SessionStateStub()

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

DATA_FILE = Path(config.SCREENER_DATA_FILE)
FIELD_DICT_FILE = Path(config.SCREENER_FIELD_DICT_FILE)

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

RESULT_TABLE_HEIGHT = 500

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

FIELD_ROW_RE = re.compile(
    r"^\|\s*`(?P<field>[^`]+)`\s*\|\s*(?P<cn_name>[^|]+?)\s*\|\s*(?P<en_desc>[^|]+?)\s*\|"
)
FORMULA_ROW_RE = re.compile(
    r"^\|\s*`(?P<field>[^`]+)`\s*\|\s*(?P<cn_desc>[^|]+?)\s*\|"
)


def expand_compound_field_key(field_key):
    """
    将类似 break_high_20/60/120/250 的复合键展开为字段列表。
    规则：
    - 如果分段后第一个 token 含 '_'，后续 token 若不含 '_' 则继承前缀。
    """
    if "/" not in field_key:
        return [field_key]

    parts = [part.strip() for part in field_key.split("/") if part.strip()]
    if not parts:
        return []

    first = parts[0]
    expanded = [first]

    if "_" in first:
        prefix = first.rsplit("_", 1)[0] + "_"
        for part in parts[1:]:
            expanded.append(part if "_" in part else f"{prefix}{part}")
    else:
        expanded.extend(parts[1:])

    return expanded


def parse_field_dictionary_markdown(markdown_text):
    """解析数据字典 markdown，返回字段元数据映射"""
    meta = {}
    formula_notes = {}
    in_formula_section = False

    for raw_line in (markdown_text or "").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue

        if "字段" in line and "中文口径" in line:
            in_formula_section = True
            continue

        if in_formula_section and line.startswith("| 字段"):
            continue

        if in_formula_section and line.startswith("|---"):
            continue

        if in_formula_section and line.count("|") < 3:
            continue

        if in_formula_section:
            match = FORMULA_ROW_RE.match(line)
            if not match:
                continue
            field_key = match.group("field").strip()
            cn_desc = match.group("cn_desc").strip()
            for field in expand_compound_field_key(field_key):
                formula_notes[field] = cn_desc
            continue

        match = FIELD_ROW_RE.match(line)
        if match:
            field = match.group("field").strip()
            cn_name = match.group("cn_name").strip()
            meta[field] = {"cn_name": cn_name, "cn_desc": ""}
            continue

    for field, cn_desc in formula_notes.items():
        meta.setdefault(field, {"cn_name": "", "cn_desc": ""})
        meta[field]["cn_desc"] = cn_desc

    return meta


@st.cache_data(show_spinner=False)
def load_field_meta(file_path=None):
    """从数据字典文件加载字段元数据"""
    target = Path(file_path) if file_path else FIELD_DICT_FILE
    if not target.exists():
        return {}
    try:
        text = target.read_text(encoding="utf-8")
    except Exception:
        return {}
    return parse_field_dictionary_markdown(text)


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

    # 静默跳过不存在字段（兼容旧快照）
    momentum_fields = [f for f in momentum_fields if f in df.columns]
    pattern_fields = [f for f in pattern_fields if f in df.columns]
    custom_rules = [r for r in custom_rules if r["field"] in df.columns]

    # 仅对 preset_rules 保留校验（预设字段应始终存在于数据文件）
    validate_required_columns(df, [rule["field"] for rule in preset_rules])

    result = df.copy()

    for field in momentum_fields + pattern_fields:
        result = result[coerce_flag_hit(result[field])]

    for rule in preset_rules + custom_rules:
        result = apply_numeric_rule(result, rule["field"], rule["operator"], rule["value"])

    return result


def is_flag_field(field):
    """判断字段是否属于 0/1 命中型信号"""
    return field.startswith("pattern_") or field.startswith("break_high_") or field in {
        "consec_up_3",
        "consec_up_5",
    }

def coerce_flag_hit(series):
    """将 flag 列兼容转换为 0/1 命中布尔掩码（兼容 str/float/bool/int）"""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().any():
        return numeric.fillna(0).astype(int) == 1
    return series.astype(str).str.strip().eq("1")


def format_display_value(field, value):
    """格式化详情展示值"""
    if is_flag_field(field):
        try:
            return "命中" if int(float(value)) == 1 else "未命中"
        except Exception:
            return "命中" if str(value).strip() == "1" else "未命中"
    return value


def find_field_group(field):
    """根据字段名找到分组"""
    for group_name, fields in FIELD_GROUPS.items():
        if field in fields:
            return group_name
    return "其他字段"


def format_stock_detail(record, field_meta=None):
    """将单条记录按分组格式化"""
    field_meta = field_meta if field_meta is not None else load_field_meta()
    detail = {group_name: [] for group_name in FIELD_GROUPS}
    detail["其他字段"] = []

    for field, value in record.items():
        group_name = find_field_group(field)
        meta = field_meta.get(field, {})
        detail[group_name].append(
            {
                "field": field,
                "value": value,
                "display_value": format_display_value(field, value),
                "cn_name": meta.get("cn_name", ""),
                "cn_desc": meta.get("cn_desc", ""),
            }
        )

    return {group: items for group, items in detail.items() if items}


def build_result_table(df):
    """构建结果表主字段"""
    available_columns = [column for column in RESULT_COLUMNS if column in df.columns]
    return df[available_columns].copy()


def get_result_table_height():
    """返回结果表固定高度"""
    return RESULT_TABLE_HEIGHT


def get_stock_record(df, ts_code):
    """根据 ts_code 获取完整记录"""
    match = df[df["ts_code"] == ts_code]
    if match.empty:
        raise ValueError(f"未找到股票记录: {ts_code}")
    return match.iloc[0].to_dict()


def init_screener_state():
    """初始化页面状态"""
    st.session_state.setdefault("screener_results", None)
    st.session_state.setdefault("screener_last_error", None)


def clear_screener_filters():
    """清空筛选状态和表单值"""
    st.session_state["screener_results"] = None
    st.session_state["screener_last_error"] = None

    if "screener_detail_input" in st.session_state:
        st.session_state["screener_detail_input"] = ""

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


def _collect_active_condition_labels():
    """从 session_state 收集所有激活的条件标签，返回字符串列表。超过10个时截断。"""
    labels = []
    for label in PRESET_RULES:
        if st.session_state.get(f"screener_preset_{label}", False):
            labels.append(label)
    for label in MOMENTUM_OPTIONS:
        if st.session_state.get(f"screener_momentum_{label}", False):
            labels.append(label)
    for label in PATTERN_OPTIONS:
        if st.session_state.get(f"screener_pattern_{label}", False):
            labels.append(label)
    for fields in CUSTOM_FILTER_GROUPS.values():
        for field in fields:
            op = st.session_state.get(f"screener_op_{field}", "不筛选")
            if op != "不筛选":
                labels.append(field)
    if len(labels) > 10:
        total = len(labels)
        shown = labels[:10]
        shown.append(f"...等{total}个条件")
        return shown
    return labels


def run_screener_filters(df):
    """根据当前 session_state 自动执行筛选"""
    selected_presets = collect_selected_options(PRESET_RULES, "screener_preset")
    selected_momentum = collect_selected_options(MOMENTUM_OPTIONS, "screener_momentum")
    selected_patterns = collect_selected_options(PATTERN_OPTIONS, "screener_pattern")
    custom_rules = collect_custom_rules()

    try:
        results = apply_screener_filters(
            df,
            selected_presets=selected_presets,
            selected_momentum=selected_momentum,
            selected_patterns=selected_patterns,
            custom_rules=custom_rules,
        )
    except ValueError as exc:
        st.session_state["screener_results"] = None
        st.session_state["screener_last_error"] = str(exc)
    else:
        st.session_state["screener_results"] = results
        st.session_state["screener_last_error"] = None


def render_toggle_group(title, option_mapping, key_prefix, columns_per_row=3):
    """渲染多选开关网格"""
    if title:  # 空字符串时不渲染标题行（tabs 场景下 title 传空字符串）
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
                [
                    {
                        "字段英文名": item["field"],
                        "中文字段名": item.get("cn_name", ""),
                        "中文说明": item.get("cn_desc", ""),
                        "值": item["display_value"],
                    }
                    for item in items
                ]
            )
            st.dataframe(detail_df, use_container_width=True, hide_index=True)


def _render_title_bar(latest_trade_date):
    """渲染标题栏: 标题 / 交易日 / 重置按钮"""
    col_title, col_date, col_reset = st.columns([3, 2, 1])
    with col_title:
        st.title("🎛️ 选股器")
    with col_date:
        st.metric("交易日", latest_trade_date)
    with col_reset:
        st.write("")  # 垂直对齐占位
        if st.button("重置条件", use_container_width=True):
            clear_screener_filters()
            st.rerun()


def _render_filter_tabs(latest_df):
    """渲染筛选区 tabs"""
    tab_preset, tab_momentum, tab_pattern, tab_custom = st.tabs(
        ["预设条件", "动量因子", "技术形态", "自定义指标"]
    )
    with tab_preset:
        render_toggle_group("", PRESET_RULES, "screener_preset", columns_per_row=2)
    with tab_momentum:
        render_toggle_group("", MOMENTUM_OPTIONS, "screener_momentum", columns_per_row=3)
    with tab_pattern:
        render_toggle_group("", PATTERN_OPTIONS, "screener_pattern", columns_per_row=4)
    with tab_custom:
        render_custom_filters(latest_df)


def _render_results_area(results):
    """渲染结果面板（results 为 None 时显示初始提示并早返回）"""
    if results is None:
        st.info("设置筛选条件后，点击「开始筛选」查看结果。")
        return

    # 已选条件摘要
    active_labels = _collect_active_condition_labels()
    label_text = " | ".join(active_labels) if active_labels else "（无）"
    st.caption(f"已选条件：{label_text}")

    # 命中数量
    col_metric, _ = st.columns([1, 3])
    with col_metric:
        st.metric("命中数量", len(results))

    # 空结果提示 / 结果表
    if results.empty:
        st.warning("暂无符合条件的股票，请调整筛选条件。")
    else:
        result_table = build_result_table(results)
        st.dataframe(
            result_table,
            use_container_width=True,
            hide_index=True,
            height=get_result_table_height(),
        )

    # 股票详情输入（有结果后始终显示，results is None 时早返回不到这里）
    ts_code_input = st.text_input(
        "查看股票详情，输入代码（如 000001.SZ）",
        key="screener_detail_input",
    )
    if ts_code_input and not results.empty:
        match = results[results["ts_code"] == ts_code_input.strip()]
        if not match.empty:
            record = match.iloc[0].to_dict()
            detail = format_stock_detail(record)
            render_stock_detail(detail)
        # 不在结果集中：静默，不报错


def render():
    """渲染选股器页面"""
    init_screener_state()

    try:
        df = load_screener_data()
    except (FileNotFoundError, ValueError) as exc:
        st.error(str(exc))
        return

    latest_trade_date = get_latest_trade_date(df)
    latest_df = df[df["trade_date"].astype(str) == latest_trade_date].copy()

    # 1. 标题栏
    _render_title_bar(latest_trade_date)

    # 2. 筛选区
    _render_filter_tabs(latest_df)

    # 3. 筛选按钮 + 错误消息
    if st.button("开始筛选", use_container_width=True, type="primary"):
        run_screener_filters(latest_df)
    if st.session_state.get("screener_last_error"):
        st.error(st.session_state["screener_last_error"])

    st.divider()

    # 4. 结果区
    _render_results_area(st.session_state.get("screener_results"))
