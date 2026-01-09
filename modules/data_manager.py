# -*- coding: utf-8 -*-
"""
数据管理模块
提供股票数据下载、更新、查询等功能
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.db_helper import (
    get_db_connection, execute_insert, execute_query,
    get_db_info, check_db_exists, execute_delete
)
from utils.baostock_client import BaostockClient


def render():
    """渲染数据管理页面"""
    st.title("📊 数据管理")

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 股票池管理",
        "⬇️ 数据下载",
        "🔄 数据更新",
        "🔍 数据查询"
    ])

    with tab1:
        render_stock_pool()

    with tab2:
        render_data_download()

    with tab3:
        render_data_update()

    with tab4:
        render_data_query()


# ============ 股票池管理 ============

def render_stock_pool():
    """渲染股票池管理页面"""

    st.subheader("股票池管理")

    # 添加股票
    with st.expander("➕ 添加股票", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            stock_input = st.text_input(
                "股票代码",
                placeholder="600519.SH 或 000001.SZ",
                help="输入格式：代码.市场，如 600519.SH（上海）或 000001.SZ（深圳）"
            )

        with col2:
            stock_name = st.text_input(
                "股票名称（可选）",
                placeholder="贵州茅台"
            )

        pool_name = st.selectbox(
            "股票池分组",
            ["default", "自选股", "沪深300", "中证500", "自定义"],
            help="选择或创建股票池分组"
        )

        note = st.text_input("备注（可选）")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("➕ 添加", type="primary"):
                if stock_input:
                    success = add_stock_to_pool(
                        stock_input,
                        stock_name if stock_name else None,
                        pool_name,
                        note if note else None
                    )
                    if success:
                        st.success(f"✅ 已添加 {stock_input} 到 {pool_name}")
                        st.rerun()
                else:
                    st.warning("⚠️ 请输入股票代码")

        with col2:
            if st.button("📥 批量导入"):
                st.info("💡 请在下方文本框中输入股票代码，每行一个")

        with col3:
            if st.button("🗑️ 清空股票池"):
                if st.session_state.get('confirm_clear', False):
                    clear_stock_pool(pool_name)
                    st.session_state.confirm_clear = False
                    st.success(f"✅ 已清空 {pool_name}")
                    st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("⚠️ 再次点击确认清空")

    st.markdown("---")

    # 批量导入
    st.markdown("#### 📥 批量导入股票")
    batch_input = st.text_area(
        "输入股票代码列表",
        placeholder="""600519.SH
000001.SZ
600036.SH
600000.SH""",
        height=150,
        help="每行一个股票代码"
    )

    if st.button("📥 批量添加"):
        if batch_input:
            codes = [line.strip() for line in batch_input.split('\n') if line.strip()]
            success_count = 0
            for code in codes:
                if add_stock_to_pool(code, None, pool_name, None):
                    success_count += 1

            st.success(f"✅ 成功添加 {success_count}/{len(codes)} 只股票")
            st.rerun()

    st.markdown("---")

    # 股票池列表
    st.markdown("#### 📋 当前股票池")

    # 获取分组统计和总数（使用缓存）
    pool_stats, total_stocks = get_pool_stats()

    if pool_stats and total_stocks > 0:
        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总股票数", total_stocks)

        with col2:
            st.metric("分组数量", len(pool_stats))

        with col3:
            default_count = pool_stats.get('default', 0)
            st.metric("默认分组", default_count)

        with col4:
            other_count = sum([v for k, v in pool_stats.items() if k != 'default'])
            st.metric("其他分组", other_count)

        st.markdown("---")

        # 分组选择器
        selected_pool = st.selectbox(
            "选择分组",
            ["全部"] + list(pool_stats.keys())
        )

        # 分页设置 - 改为每页10条
        page_size = 10

        # 初始化分页状态
        if 'pool_current_page' not in st.session_state:
            st.session_state.pool_current_page = 0
        if 'pool_last_selected' not in st.session_state:
            st.session_state.pool_last_selected = selected_pool

        # 如果分组改变，重置页码
        if st.session_state.pool_last_selected != selected_pool:
            st.session_state.pool_current_page = 0
            st.session_state.pool_last_selected = selected_pool

        # 使用数据库分页查询
        pool_filter = selected_pool if selected_pool != "全部" else None
        display_stocks, total_count = get_stock_pool(
            pool_name=pool_filter,
            page=st.session_state.pool_current_page,
            page_size=page_size
        )

        total_pages = (total_count + page_size - 1) // page_size

        # 显示当前页信息
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.info(f"📊 共 {total_count} 只股票")
        with col2:
            st.caption(f"第 {st.session_state.pool_current_page + 1}/{total_pages} 页")
        with col3:
            if st.button("🔄 重置", key="reset_pool_page"):
                st.session_state.pool_current_page = 0
                st.rerun()

        # 逐行显示股票，每行带删除按钮
        for _, row in display_stocks.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 3, 2, 2, 2, 2, 1.5])
            with col1:
                st.text(row['ts_code'])
            with col2:
                st.text(row['stock_name'] or '-')
            with col3:
                st.text(row['area'] or '-')
            with col4:
                st.text(row['industry'] or '-')
            with col5:
                st.text(row['list_date'] or '-')
            with col6:
                st.text(row['pool_name'])
            with col7:
                if st.button("🗑️", key=f"del_{row['ts_code']}", help="删除"):
                    delete_stocks_from_pool([row['ts_code']])
                    st.success(f"✅ 已删除 {row['ts_code']}")
                    st.rerun()

        # 分页按钮
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

        with col1:
            if st.button("⬅️ 首页", disabled=(st.session_state.pool_current_page == 0), key="pool_first"):
                st.session_state.pool_current_page = 0
                st.rerun()

        with col2:
            if st.button("⬅️ 上一页", disabled=(st.session_state.pool_current_page == 0), key="pool_prev"):
                st.session_state.pool_current_page = max(0, st.session_state.pool_current_page - 1)
                st.rerun()

        with col3:
            st.write(f"&nbsp;&nbsp;{st.session_state.pool_current_page + 1} / {total_pages}&nbsp;&nbsp;", unsafe_allow_html=True)

        with col4:
            if st.button("下一页 ➡️", disabled=(st.session_state.pool_current_page >= total_pages - 1), key="pool_next"):
                st.session_state.pool_current_page = min(total_pages - 1, st.session_state.pool_current_page + 1)
                st.rerun()

        with col5:
            if st.button("末页 ➡️", disabled=(st.session_state.pool_current_page >= total_pages - 1), key="pool_last"):
                st.session_state.pool_current_page = total_pages - 1
                st.rerun()

    else:
        st.info("📭 股票池为空，请添加股票")


# ============ 数据下载 ============

def render_data_download():
    """渲染数据下载页面"""

    st.subheader("数据下载")

    # 获取分组统计
    pool_stats, total_stocks = get_pool_stats()

    if total_stocks == 0:
        st.warning("⚠️ 股票池为空，请先在「股票池管理」中添加股票")
        return

    # 下载配置
    col1, col2, col3 = st.columns(3)

    with col1:
        # 按分组下载
        download_pool = st.selectbox(
            "选择分组下载",
            options=["全部"] + list(pool_stats.keys()),
            help="选择要下载的股票分组"
        )

        # 显示该分组的股票数量
        if download_pool == "全部":
            count = total_stocks
        else:
            count = pool_stats.get(download_pool, 0)
        st.info(f"📊 该分组有 {count} 只股票")

    with col2:
        frequency = st.selectbox(
            "数据周期",
            options=list(config.FREQUENCIES.keys()),
            format_func=lambda x: config.FREQUENCIES[x],
            index=0,
            help="选择数据周期"
        )

    with col3:
        date_range = st.date_input(
            "日期范围",
            value=(
                datetime.now() - timedelta(days=365),
                datetime.now()
            ),
            help="选择下载的日期范围"
        )

    # 高级选项
    with st.expander("⚙️ 高级选项"):
        col1, col2 = st.columns(2)

        with col1:
            adjustflag = st.selectbox(
                "复权类型",
                options=[1, 2, 3],
                format_func=lambda x: ["后复权", "前复权", "不复权"][x-1],
                index=1,  # 默认选择前复权（index=1 对应 value=2）
                help="选择复权方式"
            )

        with col2:
            delay = st.number_input(
                "请求延迟（秒）",
                min_value=0.0,
                max_value=5.0,
                value=0.3,  # 默认0.3秒，避免触发限流
                step=0.1,
                help="每次请求之间的延迟，避免触发API限流。建议0.3-0.5秒"
            )

    # 下载按钮
    if st.button("⬇️ 开始下载", type="primary"):
        if len(date_range) == 2:
            start_date = date_range[0].strftime("%Y-%m-%d")
            end_date = date_range[1].strftime("%Y-%m-%d")

            # 获取要下载的股票列表
            pool_filter = download_pool if download_pool != "全部" else None
            stocks_df, _ = get_stock_pool(pool_name=pool_filter, page=0, page_size=10000)

            if stocks_df is None or len(stocks_df) == 0:
                st.warning("⚠️ 该分组没有股票")
                return

            stock_codes = stocks_df['ts_code'].tolist()

            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()

            total = len(stock_codes)
            success_count = 0
            failed_stocks = []

            # 执行下载 - 在循环外创建客户端，避免重复登录
            client = BaostockClient()
            if not client.login():
                st.error("❌ 连接 baostock 失败，请检查网络")
                return

            try:
                for i, code in enumerate(stock_codes):
                    status_text.text(f"正在下载 {code} ({i+1}/{total})...")

                    try:
                        df = client.download_stock_data(
                            code,
                            start_date,
                            end_date,
                            frequency=frequency,
                            adjustflag=str(adjustflag)
                        )

                        if df is not None and not df.empty:
                            # 保存到数据库
                            save_stock_data_to_db(df, frequency)
                            success_count += 1
                        else:
                            failed_stocks.append(code)

                    except Exception as e:
                        st.error(f"❌ {code} 下载失败: {e}")
                        failed_stocks.append(code)

                    progress_bar.progress((i + 1) / total)

                    # 延迟，避免请求过快触发限流（除最后一个）
                    if i < total - 1 and delay > 0:
                        import time
                        time.sleep(delay)

            finally:
                # 确保退出登录
                client.logout()

            # 显示结果
            progress_bar.empty()
            status_text.empty()

            st.markdown("---")
            st.subheader("📊 下载结果")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("总数量", total)

            with col2:
                st.metric("成功", success_count, delta=f"{success_count/total*100:.1f}%")

            with col3:
                st.metric("失败", len(failed_stocks))

            if failed_stocks:
                st.markdown("#### ❌ 失败列表")
                for code in failed_stocks:
                    st.text(f"• {code}")

            if success_count > 0:
                st.success(f"✅ 下载完成！成功 {success_count} 只，失败 {len(failed_stocks)} 只")


# ============ 数据更新 ============

def render_data_update():
    """渲染数据更新页面"""

    st.subheader("数据更新")

    # 显示当前数据状态
    db_info = get_db_info()

    col1, col2, col3 = st.columns(3)

    with col1:
        history_count = db_info.get('stock_daily_history_count', 0)
        st.metric("日线数据", f"{history_count:,}")

    with col2:
        minute_count = db_info.get('stock_minute_history_count', 0)
        st.metric("分钟线数据", f"{minute_count:,}")

    with col3:
        indicator_count = db_info.get('stock_indicators_count', 0)
        st.metric("指标数据", f"{indicator_count:,}")

    st.markdown("---")

    # 增量更新
    st.markdown("### 🔄 增量更新")

    st.info("💡 增量更新只会下载最新的数据，不会重复下载已有数据")

    # 获取股票池
    stocks = get_stock_pool()

    if stocks is None or len(stocks) == 0:
        st.warning("⚠️ 股票池为空")
        return

    col1, col2 = st.columns(2)

    with col1:
        update_pool = st.selectbox(
            "选择股票池",
            ["全部"] + list(stocks['pool_name'].unique())
        )

    with col2:
        update_frequency = st.selectbox(
            "更新周期",
            options=list(config.FREQUENCIES.keys()),
            format_func=lambda x: config.FREQUENCIES[x],
            index=0
        )

    if st.button("🔄 开始增量更新", type="primary"):
        # 确定要更新的股票列表
        if update_pool == "全部":
            update_stocks = stocks['ts_code'].tolist()
        else:
            update_stocks = stocks[stocks['pool_name'] == update_pool]['ts_code'].tolist()

        # 获取最新日期
        last_date = get_latest_trade_date()

        if last_date:
            start_date = last_date
            end_date = datetime.now().strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")

        st.info(f"📅 更新范围: {start_date} 至 {end_date}")

        # 执行更新
        progress_bar = st.progress(0)
        status_text = st.empty()

        total = len(update_stocks)
        success_count = 0

        for i, code in enumerate(update_stocks):
            status_text.text(f"正在更新 {code} ({i+1}/{total})...")

            try:
                with BaostockClient() as client:
                    df = client.download_stock_data(
                        code,
                        start_date,
                        end_date,
                        frequency=update_frequency
                    )

                    if df is not None and not df.empty:
                        save_stock_data_to_db(df, update_frequency)
                        success_count += 1

            except Exception as e:
                st.error(f"❌ {code} 更新失败: {e}")

            progress_bar.progress((i + 1) / total)

        progress_bar.empty()
        status_text.empty()

        st.success(f"✅ 更新完成！成功 {success_count} 只")


# ============ 数据查询 ============

def render_data_query():
    """渲染数据查询页面"""

    st.subheader("数据查询")

    # 检查股票池是否有数据
    _, total_stocks = get_pool_stats()

    if total_stocks == 0:
        st.warning("⚠️ 股票池为空")
        return

    # 查询条件
    col1, col2, col3 = st.columns(3)

    with col1:
        # 使用文本输入 + 模糊搜索
        search_keyword = st.text_input(
            "搜索股票",
            placeholder="输入代码或名称，如：600519 或 茅台",
            help="支持股票代码或名称的模糊搜索"
        )

        # 如果有搜索关键词，执行搜索
        selected_stock = None
        if search_keyword and len(search_keyword.strip()) >= 2:
            search_results = search_stocks(search_keyword, limit=20)
            if len(search_results) > 0:
                options = [f"{row['ts_code']} - {row['stock_name'] or '未知'}" for _, row in search_results.iterrows()]
                selected_index = st.selectbox(
                    "搜索结果",
                    range(len(options)),
                    format_func=lambda i: options[i],
                    help="选择要查询的股票"
                )
                if selected_index is not None:
                    selected_stock = search_results.iloc[selected_index]['ts_code']
            else:
                st.info("未找到匹配的股票")
        else:
            st.caption("💡 输入至少2个字符开始搜索")

    with col2:
        query_frequency = st.selectbox(
            "数据周期",
            options=list(config.FREQUENCIES.keys()),
            format_func=lambda x: config.FREQUENCIES[x],
            index=0
        )

    with col3:
        limit = st.number_input(
            "显示条数",
            min_value=10,
            max_value=1000,
            value=100,
            step=10
        )

    # 查询按钮
    if st.button("🔍 查询", type="primary", disabled=not selected_stock):
        data = query_stock_data(selected_stock, query_frequency, limit)

        if data is not None and len(data) > 0:
            st.success(f"✅ 查询到 {len(data)} 条数据")

            # 显示统计信息
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("最新价格", f"{data['close'].iloc[0]:.2f}")

            with col2:
                change = data['close'].iloc[0] - data['close'].iloc[1]
                change_pct = (change / data['close'].iloc[1]) * 100
                st.metric("涨跌幅", f"{change_pct:+.2f}%")

            with col3:
                st.metric("最高价", f"{data['high'].max():.2f}")

            with col4:
                st.metric("最低价", f"{data['low'].min():.2f}")

            st.markdown("---")

            # 显示数据表格
            st.dataframe(
                data,
                column_config={
                    "ts_code": "代码",
                    "trade_date": "日期",
                    "open": st.column_config.NumberColumn("开盘", format="%.2f"),
                    "high": st.column_config.NumberColumn("最高", format="%.2f"),
                    "low": st.column_config.NumberColumn("最低", format="%.2f"),
                    "close": st.column_config.NumberColumn("收盘", format="%.2f"),
                    "volume": st.column_config.NumberColumn("成交量", format="%d"),
                    "amount": st.column_config.NumberColumn("成交额", format="%.0f")
                },
                use_container_width=True,
                height=400
            )

            # 导出按钮
            csv = data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 导出CSV",
                csv,
                f"{selected_stock}_{query_frequency}_data.csv",
                "text/csv"
            )
        else:
            st.warning(f"⚠️ 未找到 {selected_stock} 的 {config.FREQUENCIES[query_frequency]} 数据")


# ============ 辅助函数 ============

def search_stocks(keyword: str, limit: int = 50):
    """
    根据关键词模糊搜索股票（代码或名称）

    Args:
        keyword: 搜索关键词
        limit: 最多返回结果数

    Returns:
        DataFrame: 搜索结果
    """
    if not keyword or len(keyword.strip()) == 0:
        return pd.DataFrame()

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 同时搜索 ts_code 和 stock_name
            cursor.execute("""
                SELECT ts_code, stock_name, pool_name, area, industry, list_date
                FROM stock_pool
                WHERE ts_code LIKE ? OR stock_name LIKE ?
                ORDER BY pool_name, add_date DESC
                LIMIT ?
            """, [f'%{keyword}%', f'%{keyword}%', limit])

            result = cursor.fetchall()
            if result:
                df = pd.DataFrame([dict(row) for row in result])
                return df
            return pd.DataFrame()
    except Exception as e:
        st.error(f"搜索失败: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)  # 缓存30秒
def get_pool_stats():
    """
    获取股票池统计信息（带缓存）

    Returns:
        (pool_stats字典, 总数)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 获取分组统计
            cursor.execute("""
                SELECT pool_name, COUNT(*) as count
                FROM stock_pool
                GROUP BY pool_name
            """)
            pool_stats_raw = cursor.fetchall()
            pool_stats = {row['pool_name']: row['count'] for row in pool_stats_raw}

            # 获取总数
            cursor.execute("SELECT COUNT(*) as total FROM stock_pool")
            total_stocks = cursor.fetchone()['total']

            return pool_stats, total_stocks
    except Exception:
        return {}, 0


def add_stock_to_pool(ts_code, stock_name=None, pool_name='default', note=None):
    """添加股票到股票池"""
    try:
        data = {
            'ts_code': ts_code,
            'stock_name': stock_name,
            'pool_name': pool_name,
            'note': note
        }
        execute_insert('stock_pool', data)
        # 清除缓存
        get_pool_stats.clear()
        return True
    except Exception as e:
        st.error(f"添加失败: {e}")
        return False


def delete_stocks_from_pool(codes):
    """从股票池删除股票"""
    try:
        placeholders = ','.join(['?' for _ in codes])
        execute_delete('stock_pool', f'ts_code IN ({placeholders})', codes)
        # 清除缓存
        get_pool_stats.clear()
        return True
    except Exception as e:
        st.error(f"删除失败: {e}")
        return False


def clear_stock_pool(pool_name):
    """清空股票池"""
    try:
        execute_delete('stock_pool', 'pool_name = ?', [pool_name])
        # 清除缓存
        get_pool_stats.clear()
        return True
    except Exception as e:
        st.error(f"清空失败: {e}")
        return False


def get_stock_pool(pool_name=None, page=0, page_size=None):
    """
    获取股票池（支持分页）

    Args:
        pool_name: 分组名称，None表示全部
        page: 页码（从0开始）
        page_size: 每页大小，None表示获取全部

    Returns:
        如果page_size为None，返回完整的DataFrame
        如果指定page_size，返回 (DataFrame, total_count) 元组
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 如果指定了分页参数，使用分页查询
            if page_size is not None:
                # 先查询总数
                if pool_name:
                    count_sql = "SELECT COUNT(*) as total FROM stock_pool WHERE pool_name = ?"
                    cursor.execute(count_sql, [pool_name])
                else:
                    count_sql = "SELECT COUNT(*) as total FROM stock_pool"
                    cursor.execute(count_sql)

                total_count = cursor.fetchone()['total']

                # 查询当前页数据（明确指定列名，避免顺序问题）
                offset = page * page_size
                if pool_name:
                    data_sql = """
                        SELECT id, ts_code, stock_name, pool_name, add_date, note,
                               symbol, area, industry, list_date
                        FROM stock_pool
                        WHERE pool_name = ?
                        ORDER BY pool_name, add_date DESC
                        LIMIT ? OFFSET ?
                    """
                    cursor.execute(data_sql, [pool_name, page_size, offset])
                else:
                    data_sql = """
                        SELECT id, ts_code, stock_name, pool_name, add_date, note,
                               symbol, area, industry, list_date
                        FROM stock_pool
                        ORDER BY pool_name, add_date DESC
                        LIMIT ? OFFSET ?
                    """
                    cursor.execute(data_sql, [page_size, offset])

                result = cursor.fetchall()

                if result:
                    # 使用字典列表创建DataFrame，自动对齐列名
                    df = pd.DataFrame([dict(row) for row in result])
                    # 移除不需要显示的字段
                    df = df.drop(columns=['id', 'add_date', 'note', 'symbol'], errors='ignore')
                    return df, total_count
                else:
                    return pd.DataFrame(), total_count

            else:
                # 不分页，获取全部数据（明确指定列名）
                if pool_name:
                    sql = """
                        SELECT id, ts_code, stock_name, pool_name, add_date, note,
                               symbol, area, industry, list_date
                        FROM stock_pool
                        WHERE pool_name = ?
                        ORDER BY add_date DESC
                    """
                    cursor.execute(sql, [pool_name])
                else:
                    sql = """
                        SELECT id, ts_code, stock_name, pool_name, add_date, note,
                               symbol, area, industry, list_date
                        FROM stock_pool
                        ORDER BY pool_name, add_date DESC
                    """
                    cursor.execute(sql)

                result = cursor.fetchall()

                if result:
                    # 使用字典列表创建DataFrame，自动对齐列名
                    df = pd.DataFrame([dict(row) for row in result])
                    # 移除不需要显示的字段
                    df = df.drop(columns=['id', 'add_date', 'note', 'symbol'], errors='ignore')
                    return df
                return pd.DataFrame()

    except Exception as e:
        st.error(f"获取股票池失败: {e}")
        if page_size is not None:
            return pd.DataFrame(), 0
        return pd.DataFrame()


def save_stock_data_to_db(df, frequency='d'):
    """保存股票数据到数据库"""
    try:
        with get_db_connection() as conn:
            # 根据频率选择表和字段
            if frequency == 'd':
                table_name = 'stock_daily_history'
                date_col = 'trade_date'
                # 日线表有 turnover_ratio 字段
                columns = f'ts_code, {date_col}, open, high, low, close, volume, amount, turnover_ratio'
                placeholders = '?, ?, ?, ?, ?, ?, ?, ?, ?'
            else:
                table_name = 'stock_minute_history'
                date_col = 'timestamp'
                # 分钟线表没有 turnover_ratio 字段
                columns = f'ts_code, {date_col}, frequency, open, high, low, close, volume, amount'
                placeholders = '?, ?, ?, ?, ?, ?, ?, ?, ?'

            # 重命名列
            df = df.rename(columns={'date': 'trade_date'})

            # 保存数据
            for _, row in df.iterrows():
                if frequency == 'd':
                    # 日线数据包含 turnover_ratio
                    values = (
                        row['code'],
                        row['trade_date'],
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume'],
                        row['amount'],
                        row['turn'] if 'turn' in row else None
                    )
                else:
                    # 分钟线数据不包含 turnover_ratio
                    values = (
                        row['code'],
                        row['trade_date'],
                        frequency,
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume'],
                        row['amount']
                    )

                conn.execute(f"""
                    INSERT OR REPLACE INTO {table_name}
                    ({columns})
                    VALUES ({placeholders})
                """, values)

            conn.commit()
            return True

    except Exception as e:
        st.error(f"保存数据失败: {e}")
        return False


def get_latest_trade_date():
    """获取最新交易日期"""
    try:
        sql = "SELECT MAX(trade_date) as max_date FROM stock_daily_history"
        result = execute_query(sql, fetch_one=True)
        if result and result['max_date']:
            return result['max_date']
        return None
    except Exception as e:
        return None


def query_stock_data(ts_code, frequency='d', limit=100):
    """查询股票数据"""
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
            return pd.DataFrame(results, columns=columns)
        return None

    except Exception as e:
        st.error(f"查询数据失败: {e}")
        return None
