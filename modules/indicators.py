# -*- coding: utf-8 -*-
"""
技术指标模块
提供技术指标计算和可视化功能
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
from datetime import date, timedelta

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.db_helper import execute_query, get_db_connection
from utils.indicator_calc import calculate_all_indicators


def render():
    """渲染技术指标页面"""
    st.title("📈 技术指标")

    # 创建标签页
    tab1, tab2, tab3 = st.tabs([
        "📊 指标计算",
        "📉 K线图表",
        "📋 指标查询"
    ])

    with tab1:
        render_indicator_calculate()

    with tab2:
        render_kline_chart()

    with tab3:
        render_indicator_query()


# ============ 指标计算 ============

def render_indicator_calculate():
    """渲染指标计算页面"""

    st.subheader("技术指标计算")

    # 获取股票列表
    from modules.data_manager import get_stock_pool
    stocks = get_stock_pool()

    if stocks is None or len(stocks) == 0:
        st.warning("⚠️ 股票池为空，请先在数据管理中添加股票")
        return

    # 只保留批量计算功能
    render_batch_calculation(stocks)


def render_single_stock_calculation(stocks):
    """渲染单只股票计算界面"""

    # 选择股票
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_stock = st.selectbox(
            "选择股票",
            options=stocks['ts_code'].tolist(),
            format_func=lambda x: f"{x} - {stocks[stocks['ts_code']==x]['stock_name'].values[0] if stocks[stocks['ts_code']==x]['stock_name'].values[0] else '未知'}"
        )

    with col2:
        frequency = st.selectbox(
            "数据周期",
            options=list(config.FREQUENCIES.keys()),
            format_func=lambda x: config.FREQUENCIES[x],
            index=0
        )

    with col3:
        limit = st.number_input(
            "计算条数",
            min_value=30,
            max_value=1000,
            value=100,
            step=10,
            help="至少需要30条数据才能计算所有指标"
        )

    # 初始化 session state
    if 'calculated_indicators' not in st.session_state:
        st.session_state.calculated_indicators = None
    if 'selected_stock_code' not in st.session_state:
        st.session_state.selected_stock_code = None

    # 计算按钮
    if st.button("🧮 计算指标", type="primary"):
        with st.spinner("正在计算技术指标..."):
            # 获取历史数据
            data = get_stock_data(selected_stock, frequency, limit)

            if data is not None and len(data) > 30:
                # 计算指标
                data = calculate_all_indicators(data)

                st.success(f"✅ 计算完成！共 {len(data)} 条数据")

                # 保存到数据库（只保存最后一天）
                success = save_indicators_to_db(selected_stock, data, frequency, save_all=False)

                if success:
                    latest_date = data.iloc[-1]['trade_date']
                    st.success(f"✅ 已保存最新交易日 ({latest_date}) 的指标到数据库")

                # 保存到 session state
                st.session_state.calculated_indicators = data
                st.session_state.selected_stock_code = selected_stock

            else:
                st.error(f"❌ 数据不足，至少需要30条数据，当前只有 {len(data) if data is not None else 0} 条")
                st.session_state.calculated_indicators = None

    # 显示计算结果
    if st.session_state.calculated_indicators is not None:
        data = st.session_state.calculated_indicators

        st.markdown("#### 📊 指标预览")

        # 选择要显示的指标
        indicator_groups = {
            "MA均线": ['ma5', 'ma10', 'ma20', 'ma60'],
            "MACD": ['dif', 'dea', 'macd'],
            "KDJ": ['k', 'd', 'j'],
            "RSI": ['rsi6', 'rsi12', 'rsi24'],
            "布林带": ['boll_upper', 'boll_mid', 'boll_lower'],
            "其他": ['change_pct', 'change_5d', 'atr14']
        }

        selected_group = st.selectbox(
            "选择指标组",
            options=list(indicator_groups.keys()),
            key="indicator_group_select"
        )

        indicators = indicator_groups[selected_group]

        # 显示指标数据
        display_cols = ['trade_date', 'close'] + indicators
        display_data = data[display_cols].copy()

        # 格式化显示
        for col in indicators:
            if col in display_data.columns:
                display_data[col] = display_data[col].round(4)

        st.dataframe(
            display_data,
            column_config={col: col.upper() for col in display_data.columns},
            use_container_width=True
        )


def render_batch_calculation(stocks):
    """渲染批量计算界面"""

    import time
    from utils.db_helper import get_latest_trade_date

    # 简化的界面：只显示关键信息
    col1, col2 = st.columns(2)

    with col1:
        frequency = st.selectbox(
            "数据周期",
            options=list(config.FREQUENCIES.keys()),
            format_func=lambda x: config.FREQUENCIES[x],
            index=0,
            key="batch_freq"
        )

    with col2:
        # 获取最近交易日
        latest_trade_date = get_latest_trade_date()
        st.info(f"📅 最近交易日: {latest_trade_date}")

    # 说明信息
    st.info("💡 将计算股票池中所有股票的技术指标，自动加载100天历史数据以保证指标准确性")

    # 批量计算选项
    with st.expander("⚙️ 批量计算选项", expanded=False):
        skip_calculated = st.checkbox(
            "跳过已计算的股票",
            value=True,
            help="如果股票已计算最新交易日的指标，则跳过"
        )

    # 显示统计信息
    stock_count = len(stocks)
    st.info(f"📊 股票池共有 {stock_count} 只股票")

    # 批量计算按钮
    if st.button("🚀 开始批量计算", type="primary"):
        # 初始化进度
        progress_bar = st.progress(0, text="准备开始...")
        status_text = st.empty()

        # 统计信息
        success_count = 0
        failed_count = 0
        skipped_count = 0
        failed_stocks = []

        start_time = time.time()
        limit = 100  # 固定加载100天数据

        # 遍历所有股票
        for i, stock in stocks.iterrows():
            ts_code = stock['ts_code']
            stock_name = stock['stock_name']

            # 更新进度
            progress = (i + 1) / stock_count
            progress_bar.progress(progress, text=f"正在处理 {ts_code} ({i+1}/{stock_count})")
            status_text.text(f"当前: {ts_code} - {stock_name}")

            try:
                # 智能检测：检查是否已计算
                if skip_calculated:
                    already_calculated = check_indicator_calculated(ts_code, latest_trade_date, frequency)
                    if already_calculated:
                        skipped_count += 1
                        continue

                # 获取历史数据
                data = get_stock_data(ts_code, frequency, limit)

                if data is None or len(data) < 30:
                    failed_count += 1
                    failed_stocks.append(f"{ts_code} - {stock_name} (数据不足)")
                    continue

                # 计算指标
                data = calculate_all_indicators(data)

                # 保存到数据库（只保存最后一天）
                success = save_indicators_to_db(ts_code, data, frequency, save_all=False)

                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    failed_stocks.append(f"{ts_code} - {stock_name} (保存失败)")

            except Exception as e:
                failed_count += 1
                failed_stocks.append(f"{ts_code} - {stock_name} (错误: {str(e)})")

        # 计算耗时
        elapsed_time = time.time() - start_time

        # 清除进度条
        progress_bar.empty()
        status_text.empty()

        # 显示统计结果
        st.markdown("---")
        st.subheader("📊 批量计算完成")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("✅ 成功", success_count)

        with col2:
            st.metric("⏭️ 跳过", skipped_count)

        with col3:
            st.metric("❌ 失败", failed_count)

        with col4:
            st.metric("⏱️ 耗时", f"{elapsed_time:.1f}秒")

        # 显示失败列表
        if failed_stocks:
            with st.expander(f"❌ 失败股票列表 ({len(failed_stocks)})"):
                for stock in failed_stocks:
                    st.text(stock)

        # 显示成功率
        if success_count + failed_count > 0:
            success_rate = success_count / (success_count + failed_count) * 100
            st.success(f"🎉 成功率: {success_rate:.1f}%")


# ============ K线图表 ============

def render_kline_chart():
    """渲染K线图页面"""

    st.subheader("K线图表")

    # 获取股票列表
    from modules.data_manager import get_stock_pool
    stocks = get_stock_pool()

    if stocks is None or len(stocks) == 0:
        st.warning("⚠️ 股票池为空")
        return

    # 选择条件
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_stock = st.selectbox(
            "选择股票",
            options=stocks['ts_code'].tolist(),
            format_func=lambda x: f"{x} - {stocks[stocks['ts_code']==x]['stock_name'].values[0] if stocks[stocks['ts_code']==x]['stock_name'].values[0] else '未知'}",
            key="chart_stock"
        )

    with col2:
        frequency = st.selectbox(
            "数据周期",
            options=list(config.FREQUENCIES.keys()),
            format_func=lambda x: config.FREQUENCIES[x],
            index=0,
            key="chart_freq"
        )

    with col3:
        days = st.number_input(
            "显示天数",
            min_value=30,
            max_value=500,
            value=60,
            step=10,
            key="chart_days"
        )

    with col4:
        show_indicators = st.multiselect(
            "显示指标",
            options=["MA均线", "MACD", "KDJ", "RSI", "BOLL", "成交量"],
            default=["MA均线", "成交量"]
        )

    # 绘图按钮
    if st.button("📈 绘制图表", type="primary"):
        with st.spinner("正在生成图表..."):
            # 获取数据和指标
            data = get_stock_data_with_indicators(selected_stock, frequency, days)

            if data is not None and len(data) > 0:
                # 绘制图表
                fig = create_kline_chart(data, show_indicators)

                if fig:
                    st.plotly_chart(fig, use_container_width=True)

                    # 显示统计信息
                    display_stock_stats(data)

            else:
                st.warning("⚠️ 没有找到数据")


# ============ 指标查询 ============

def render_indicator_query():
    """渲染指标查询页面"""

    st.subheader("指标查询")

    # 初始化 session state
    if 'query_indicators_data' not in st.session_state:
        st.session_state.query_indicators_data = None
    if 'query_indicators_stock' not in st.session_state:
        st.session_state.query_indicators_stock = None
    if 'db_query_indicators_data' not in st.session_state:
        st.session_state.db_query_indicators_data = None
    if 'db_query_indicators_stock' not in st.session_state:
        st.session_state.db_query_indicators_stock = None

    # 获取股票列表
    from modules.data_manager import get_stock_pool
    stocks = get_stock_pool()

    if stocks is None or len(stocks) == 0:
        st.warning("⚠️ 股票池为空")
        return

    # 查询方式切换
    mode = st.radio("查询方式", ["数据库", "内存计算"], horizontal=True, key="indicator_query_mode")

    # ========== 模式一：数据库查询 ==========
    if mode == "数据库":
        # 条件区域
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            db_query_stock = st.selectbox(
                "选择股票",
                options=stocks['ts_code'].tolist(),
                format_func=lambda x: f"{x} - {stocks[stocks['ts_code']==x]['stock_name'].values[0] if stocks[stocks['ts_code']==x]['stock_name'].values[0] else '未知'}",
                key="db_query_stock"
            )

        with col2:
            db_query_freq = st.selectbox(
                "数据周期",
                options=list(config.FREQUENCIES.keys()),
                format_func=lambda x: config.FREQUENCIES[x],
                index=0,
                key="db_query_freq"
            )

        with col3:
            # 默认查询最近90天
            default_start = date.today() - timedelta(days=90)
            db_query_start = st.date_input("开始日期", value=default_start, key="db_query_start")

        with col4:
            db_query_end = st.date_input("结束日期", value=date.today(), key="db_query_end")

        include_price = st.checkbox("包含价格数据", value=True, help="联接日线数据以展示开高低收与成交量")

        if st.button("🔍 查询（数据库）", type="primary"):
            if db_query_start > db_query_end:
                st.error("❌ 开始日期不能晚于结束日期")
            else:
                with st.spinner("正在读取数据库..."):
                    df = query_indicators_from_db(
                        ts_code=db_query_stock,
                        frequency=db_query_freq,
                        start_date=db_query_start.isoformat(),
                        end_date=db_query_end.isoformat(),
                        include_price=include_price
                    )
                    if df is None or len(df) == 0:
                        st.info("数据库未找到符合条件的指标记录。")
                        st.session_state.db_query_indicators_data = None
                    else:
                        st.success(f"✅ 查询到 {len(df)} 条记录")
                        st.session_state.db_query_indicators_data = df
                        st.session_state.db_query_indicators_stock = db_query_stock

        if st.session_state.db_query_indicators_data is not None:
            indicators = st.session_state.db_query_indicators_data
            # 最新值
            st.markdown("#### 📊 最新指标值（数据库）")
            latest = indicators.iloc[-1]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("MA5", f"{latest.get('ma5', 0):.2f}" if pd.notna(latest.get('ma5')) else "-")
                st.metric("MA20", f"{latest.get('ma20', 0):.2f}" if pd.notna(latest.get('ma20')) else "-")
            with col2:
                st.metric("MACD", f"{latest.get('macd', 0):.4f}" if pd.notna(latest.get('macd')) else "-")
                st.metric("KDJ_K", f"{latest.get('k', 0):.2f}" if pd.notna(latest.get('k')) else "-")
            with col3:
                st.metric("RSI6", f"{latest.get('rsi6', 0):.2f}" if pd.notna(latest.get('rsi6')) else "-")
                st.metric("BOLL上轨", f"{latest.get('boll_upper', 0):.2f}" if pd.notna(latest.get('boll_upper')) else "-")
            with col4:
                st.metric("涨跌幅", f"{latest.get('change_pct', 0):.2f}%" if pd.notna(latest.get('change_pct')) else "-")
                st.metric("ATR14", f"{latest.get('atr14', 0):.2f}" if pd.notna(latest.get('atr14')) else "-")

            st.markdown("---")

            st.markdown("#### 📋 指标详情（数据库）")
            available_columns = indicators.columns.tolist()
            default_columns = [col for col in ['trade_date', 'open', 'high', 'low', 'close', 'volume',
                                               'ma5', 'ma10', 'ma20', 'ma60',
                                               'dif', 'dea', 'macd', 'k', 'd', 'j',
                                               'rsi6', 'rsi12', 'rsi24',
                                               'boll_upper', 'boll_mid', 'boll_lower',
                                               'change_pct', 'atr14'] if col in available_columns]
            display_columns = st.multiselect(
                "选择要显示的列",
                options=available_columns,
                default=default_columns[:12],
                key="db_query_display_columns"
            )
            if display_columns:
                st.dataframe(indicators[display_columns], use_container_width=True)
                csv = indicators[display_columns].to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 导出CSV（数据库）",
                    csv,
                    f"{st.session_state.db_query_indicators_stock}_indicators_db.csv",
                    "text/csv"
                )

        st.markdown("---")

    # ========== 模式二：内存计算 ==========
    if mode == "内存计算":
        # 查询条件
        col1, col2, col3 = st.columns(3)

        with col1:
            query_stock = st.selectbox(
                "选择股票",
                options=stocks['ts_code'].tolist(),
                format_func=lambda x: f"{x} - {stocks[stocks['ts_code']==x]['stock_name'].values[0] if stocks[stocks['ts_code']==x]['stock_name'].values[0] else '未知'}",
                key="query_stock"
            )

        with col2:
            query_freq = st.selectbox(
                "数据周期",
                options=list(config.FREQUENCIES.keys()),
                format_func=lambda x: config.FREQUENCIES[x],
                index=0,
                key="query_freq"
            )

        with col3:
            query_limit = st.number_input(
                "显示条数",
                min_value=10,
                max_value=500,
                value=100,
                step=10,
                help="加载历史数据天数，建议至少60天以观察指标趋势"
            )

        st.info("💡 实时计算指标数据（内存计算），用于快速查看和分析，不保存到数据库")

        if st.button("🔍 查询（内存）", type="primary"):
            with st.spinner("正在计算指标..."):
                data = get_stock_data(query_stock, query_freq, query_limit)
                if data is not None and len(data) > 0:
                    indicators = calculate_all_indicators(data)
                    st.success(f"✅ 计算完成！共 {len(indicators)} 条数据")
                    st.session_state.query_indicators_data = indicators
                    st.session_state.query_indicators_stock = query_stock
                else:
                    st.error(f"❌ 没有找到 {query_stock} 的历史数据")
                    st.session_state.query_indicators_data = None

        # 显示查询结果（内存）
        if st.session_state.query_indicators_data is not None:
            indicators = st.session_state.query_indicators_data
            st.markdown("#### 📊 最新指标值（内存）")
            latest = indicators.iloc[-1]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("MA5", f"{latest.get('ma5', 0):.2f}" if pd.notna(latest.get('ma5')) else "-")
                st.metric("MA20", f"{latest.get('ma20', 0):.2f}" if pd.notna(latest.get('ma20')) else "-")
            with col2:
                st.metric("MACD", f"{latest.get('macd', 0):.4f}" if pd.notna(latest.get('macd')) else "-")
                st.metric("KDJ_K", f"{latest.get('k', 0):.2f}" if pd.notna(latest.get('k')) else "-")
            with col3:
                st.metric("RSI6", f"{latest.get('rsi6', 0):.2f}" if pd.notna(latest.get('rsi6')) else "-")
                st.metric("BOLL上轨", f"{latest.get('boll_upper', 0):.2f}" if pd.notna(latest.get('boll_upper')) else "-")
            with col4:
                st.metric("涨跌幅", f"{latest.get('change_pct', 0):.2f}%" if pd.notna(latest.get('change_pct')) else "-")
                st.metric("振幅", f"{latest.get('amplitude', 0):.2f}%" if pd.notna(latest.get('amplitude')) else "-")

            st.markdown("---")

            st.markdown("#### 📋 指标详情（内存）")
            available_columns = indicators.columns.tolist()
            default_columns = [col for col in ['trade_date', 'close', 'ma5', 'ma10', 'ma20', 'ma60',
                                               'dif', 'dea', 'macd', 'k', 'd', 'j',
                                               'rsi6', 'rsi12', 'rsi24',
                                               'boll_upper', 'boll_mid', 'boll_lower',
                                               'change_pct', 'atr14'] if col in available_columns]
            display_columns = st.multiselect(
                "选择要显示的指标",
                options=available_columns,
                default=default_columns[:12],
                key="query_display_columns"
            )
            if display_columns:
                st.dataframe(indicators[display_columns], use_container_width=True)
                csv = indicators[display_columns].to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 导出CSV（内存）",
                    csv,
                    f"{st.session_state.query_indicators_stock}_indicators.csv",
                    "text/csv"
                )


# ============ 辅助函数 ============

def get_stock_data(ts_code, frequency='d', limit=100):
    """获取股票数据"""
    try:
        if frequency == 'd':
            table_name = 'stock_daily_history'
            date_col = 'trade_date'
        else:
            table_name = 'stock_minute_history'
            date_col = 'timestamp'

        sql = f"""
            SELECT ts_code, {date_col} as trade_date,
                   open, high, low, close, volume, amount
            FROM {table_name}
            WHERE ts_code = ?
            ORDER BY {date_col} DESC
            LIMIT ?
        """

        results = execute_query(sql, [ts_code, limit], fetch_all=True)

        if results:
            columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount']
            df = pd.DataFrame(results, columns=columns)
            df = df.sort_values('trade_date')
            return df
        return None

    except Exception as e:
        st.error(f"获取数据失败: {e}")
        return None


def get_stock_data_with_indicators(ts_code, frequency='d', limit=100):
    """获取带指标的股票数据"""
    try:
        if frequency == 'd':
            date_col = 'h.trade_date'
        else:
            date_col = 'h.timestamp'

        sql = f"""
            SELECT
                h.ts_code,
                {date_col} as trade_date,
                h.open, h.high, h.low, h.close, h.volume, h.amount,
                i.ma5, i.ma10, i.ma20, i.ma60,
                i.dif, i.dea, i.macd,
                i.k, i.d, i.j,
                i.rsi6, i.rsi12, i.rsi24,
                i.boll_upper, i.boll_mid, i.boll_lower,
                i.atr14, i.change_pct
            FROM stock_daily_history h
            LEFT JOIN stock_indicators i ON h.ts_code = i.ts_code AND h.trade_date = i.trade_date
            WHERE h.ts_code = ?
            ORDER BY h.trade_date DESC
            LIMIT ?
        """

        results = execute_query(sql, [ts_code, limit], fetch_all=True)

        if results:
            columns = [
                'ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                'ma5', 'ma10', 'ma20', 'ma60',
                'dif', 'dea', 'macd',
                'k', 'd', 'j',
                'rsi6', 'rsi12', 'rsi24',
                'boll_upper', 'boll_mid', 'boll_lower',
                'atr14', 'change_pct'
            ]
            df = pd.DataFrame(results, columns=columns)
            df = df.sort_values('trade_date')
            return df
        return None

    except Exception as e:
        st.error(f"获取数据失败: {e}")
        return None


def get_indicators(ts_code, frequency='d', limit=100):
    """获取指标数据"""
    try:
        if frequency == 'd':
            date_col = 'trade_date'
        else:
            date_col = 'timestamp'

        sql = f"""
            SELECT *
            FROM stock_indicators
            WHERE ts_code = ? AND frequency = ?
            ORDER BY {date_col} DESC
            LIMIT ?
        """

        results = execute_query(sql, [ts_code, frequency, limit], fetch_all=True)

        if results:
            columns = [
                'ts_code', 'trade_date', 'frequency',
                'ma5', 'ma10', 'ma20', 'ma60',
                'vma5', 'vma10',
                'change_pct', 'change_5d',
                'dif', 'dea', 'macd',
                'k', 'd', 'j',
                'rsi6', 'rsi12', 'rsi24',
                'boll_upper', 'boll_mid', 'boll_lower',
                'atr14'
            ]
            df = pd.DataFrame(results, columns=columns)
            return df
        return None

    except Exception as e:
        st.error(f"获取指标失败: {e}")
        return None


def save_indicators_to_db(ts_code, df, frequency='d', save_all=False):
    """保存指标到数据库"""
    try:
        from utils.indicator_calc import save_indicators_to_db as save
        return save(ts_code, df, frequency, save_all)
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False


def query_indicators_from_db(ts_code, start_date, end_date, frequency='d', include_price=True):
    """按日期范围查询数据库中的指标数据

    参数:
        ts_code: 股票代码
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        frequency: 周期，默认为 'd'
        include_price: 是否联接日线表以包含价格字段

    返回:
        DataFrame 或 None
    """
    try:
        if include_price:
            sql = """
                SELECT
                    i.ts_code,
                    i.trade_date,
                    i.frequency,
                    h.open, h.high, h.low, h.close, h.volume, h.amount,
                    i.ma5, i.ma10, i.ma20, i.ma60,
                    i.vma5, i.vma10,
                    i.change_pct, i.change_5d,
                    i.dif, i.dea, i.macd,
                    i.k, i.d, i.j,
                    i.rsi6, i.rsi12, i.rsi24,
                    i.boll_upper, i.boll_mid, i.boll_lower,
                    i.atr14
                FROM stock_indicators i
                LEFT JOIN stock_daily_history h
                    ON i.ts_code = h.ts_code AND i.trade_date = h.trade_date
                WHERE i.ts_code = ? AND i.frequency = ? AND i.trade_date BETWEEN ? AND ?
                ORDER BY i.trade_date ASC
            """
            params = [ts_code, frequency, start_date, end_date]
            columns = [
                'ts_code', 'trade_date', 'frequency',
                'open', 'high', 'low', 'close', 'volume', 'amount',
                'ma5', 'ma10', 'ma20', 'ma60',
                'vma5', 'vma10',
                'change_pct', 'change_5d',
                'dif', 'dea', 'macd',
                'k', 'd', 'j',
                'rsi6', 'rsi12', 'rsi24',
                'boll_upper', 'boll_mid', 'boll_lower',
                'atr14'
            ]
        else:
            sql = """
                SELECT
                    ts_code, trade_date, frequency,
                    ma5, ma10, ma20, ma60,
                    vma5, vma10,
                    change_pct, change_5d,
                    dif, dea, macd,
                    k, d, j,
                    rsi6, rsi12, rsi24,
                    boll_upper, boll_mid, boll_lower,
                    atr14
                FROM stock_indicators
                WHERE ts_code = ? AND frequency = ? AND trade_date BETWEEN ? AND ?
                ORDER BY trade_date ASC
            """
            params = [ts_code, frequency, start_date, end_date]
            columns = [
                'ts_code', 'trade_date', 'frequency',
                'ma5', 'ma10', 'ma20', 'ma60',
                'vma5', 'vma10',
                'change_pct', 'change_5d',
                'dif', 'dea', 'macd',
                'k', 'd', 'j',
                'rsi6', 'rsi12', 'rsi24',
                'boll_upper', 'boll_mid', 'boll_lower',
                'atr14'
            ]

        results = execute_query(sql, params, fetch_all=True)
        if results:
            df = pd.DataFrame(results, columns=columns)
            df = df.sort_values('trade_date')
            return df
        return None
    except Exception as e:
        st.error(f"查询指标失败: {e}")
        return None


def create_kline_chart(data, show_indicators):
    """创建K线图表"""

    if data is None or len(data) == 0:
        return None

    # 计算子图数量
    subplot_count = 1  # K线图
    if "MACD" in show_indicators:
        subplot_count += 1
    if "KDJ" in show_indicators:
        subplot_count += 1
    if "RSI" in show_indicators:
        subplot_count += 1
    if "成交量" in show_indicators:
        subplot_count += 1

    # 创建子图
    row_heights = [0.5] + [0.15] * (subplot_count - 1)

    fig = make_subplots(
        rows=subplot_count,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights
    )

    # K线图
    candlestick = go.Candlestick(
        x=data['trade_date'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='K线'
    )
    fig.add_trace(candlestick, row=1, col=1)

    # MA均线
    if "MA均线" in show_indicators:
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        mas = ['ma5', 'ma10', 'ma20', 'ma60']
        for i, ma in enumerate(mas):
            if ma in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data['trade_date'],
                        y=data[ma],
                        name=ma.upper(),
                        line=dict(color=colors[i], width=1)
                    ),
                    row=1, col=1
                )

    # 布林带
    if "BOLL" in show_indicators:
        if 'boll_upper' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['boll_upper'],
                    name='BOLL上轨',
                    line=dict(color='rgba(255,0,0,0.3)', width=1),
                    fill=None
                ),
                row=1, col=1
            )
        if 'boll_lower' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['boll_lower'],
                    name='BOLL下轨',
                    line=dict(color='rgba(255,0,0,0.3)', width=1),
                    fill='tonexty',
                    fillcolor='rgba(255,0,0,0.05)'
                ),
                row=1, col=1
            )

    current_row = 2

    # MACD
    if "MACD" in show_indicators:
        if 'dif' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['dif'],
                    name='DIF',
                    line=dict(color='#FF6B6B', width=1.5)
                ),
                row=current_row, col=1
            )
        if 'dea' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['dea'],
                    name='DEA',
                    line=dict(color='#4ECDC4', width=1.5)
                ),
                row=current_row, col=1
            )
        if 'macd' in data.columns:
            colors = ['red' if x >= 0 else 'green' for x in data['macd']]
            fig.add_trace(
                go.Bar(
                    x=data['trade_date'],
                    y=data['macd'],
                    name='MACD',
                    marker_color=colors
                ),
                row=current_row, col=1
            )
        current_row += 1

    # KDJ
    if "KDJ" in show_indicators:
        if 'k' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['k'],
                    name='K',
                    line=dict(color='#FF6B6B', width=1.5)
                ),
                row=current_row, col=1
            )
        if 'd' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['d'],
                    name='D',
                    line=dict(color='#4ECDC4', width=1.5)
                ),
                row=current_row, col=1
            )
        if 'j' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['j'],
                    name='J',
                    line=dict(color='#45B7D1', width=1.5)
                ),
                row=current_row, col=1
            )

        # 添加超买超卖线
        fig.add_hline(y=80, line_dash="dash", line_color="red", row=current_row, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="green", row=current_row, col=1)
        current_row += 1

    # RSI
    if "RSI" in show_indicators:
        if 'rsi6' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['rsi6'],
                    name='RSI6',
                    line=dict(color='#FF6B6B', width=1.5)
                ),
                row=current_row, col=1
            )

        # 添加超买超卖线
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
        current_row += 1

    # 成交量
    if "成交量" in show_indicators:
        colors = ['red' if row['close'] >= row['open'] else 'green'
                  for _, row in data.iterrows()]
        fig.add_trace(
            go.Bar(
                x=data['trade_date'],
                y=data['volume'],
                name='成交量',
                marker_color=colors
            ),
            row=current_row, col=1
        )

    # 更新布局
    fig.update_layout(
        title=f"{data['ts_code'].iloc[0]} K线图",
        xaxis_rangeslider_visible=False,
        height=200 * subplot_count,
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


def display_stock_stats(data):
    """显示股票统计信息"""
    if data is None or len(data) == 0:
        return

    latest = data.iloc[-1]

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("最新价", f"{latest['close']:.2f}")

    with col2:
        change = latest['close'] - data['close'].iloc[-2]
        change_pct = (change / data['close'].iloc[-2]) * 100
        st.metric("涨跌幅", f"{change_pct:+.2f}%")

    with col3:
        st.metric("最高", f"{latest['high']:.2f}")

    with col4:
        st.metric("最低", f"{latest['low']:.2f}")

    with col5:
        st.metric("成交量", f"{latest['volume']:.0f}")


def check_indicator_calculated(ts_code, target_date, frequency='d'):
    """
    检查指定股票的指标是否已计算到目标日期

    参数:
        ts_code: 股票代码
        target_date: 目标日期
        frequency: 数据周期

    返回:
        bool: True表示已计算，False表示未计算
    """
    try:
        from utils.db_helper import get_db_connection

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 查询该股票最新的指标日期
            cursor.execute("""
                SELECT trade_date
                FROM stock_indicators
                WHERE ts_code = ? AND frequency = ?
                ORDER BY trade_date DESC
                LIMIT 1
            """, (ts_code, frequency))

            result = cursor.fetchone()

            if result:
                latest_calculated_date = result['trade_date']
                # 如果最新计算日期 >= 目标日期，认为已计算
                return latest_calculated_date >= target_date
            else:
                # 没有找到记录，未计算
                return False

    except Exception as e:
        st.error(f"检查指标计算状态失败: {e}")
        return False
