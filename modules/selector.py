# -*- coding: utf-8 -*-
"""
选股执行模块
提供策略执行和结果展示功能
"""

import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.db_helper import execute_query, get_db_connection, execute_insert


def render():
    """渲染选股执行页面"""
    st.title("🎯 执行选股")

    # 创建标签页
    tab1, tab2, tab3 = st.tabs([
        "⚡ 执行选股",
        "📊 历史记录",
        "📋 结果对比"
    ])

    with tab1:
        render_selection_execute()

    with tab2:
        render_selection_history()

    with tab3:
        render_result_comparison()


# ============ 执行选股 ============

def render_selection_execute():
    """渲染选股执行页面"""

    st.subheader("策略选股")

    # 获取用户策略
    strategies = get_user_strategies()

    if strategies is None or len(strategies) == 0:
        st.warning("⚠️ 你还没有保存任何策略，请先在「策略配置」中创建策略")
        return

    # 获取股票池
    from modules.data_manager import get_stock_pool
    stocks = get_stock_pool()

    if stocks is None or len(stocks) == 0:
        st.warning("⚠️ 股票池为空，请先在「数据管理」中添加股票")
        return

    # 选股配置
    col1, col2, col3 = st.columns(3)

    with col1:
        # 选择策略
        strategy_options = strategies['strategy_name'].tolist()
        selected_strategy = st.selectbox(
            "选择策略",
            options=strategy_options,
            help="选择要执行的策略"
        )

    with col2:
        # 选择股票池
        pool_options = ["全部"] + list(stocks['pool_name'].unique())
        selected_pool = st.selectbox(
            "选择股票池",
            options=pool_options,
            help="选择选股范围"
        )

    with col3:
        # 选择日期
        execute_date = st.date_input(
            "选股日期",
            value=pd.Timestamp.now(),
            help="选择哪一天的数据进行选股"
        )

    st.markdown("---")

    # 显示策略信息
    strategy_info = strategies[strategies['strategy_name'] == selected_strategy].iloc[0]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"**类型**: {strategy_info['strategy_type']}")

    with col2:
        st.info(f"**模板**: {strategy_info['template_name']}")

    with col3:
        if strategy_info['description']:
            st.info(f"**说明**: {strategy_info['description']}")

    st.markdown("---")

    # 执行按钮
    col1, col2 = st.columns(2)

    with col1:
        execute_button = st.button("🎯 开始选股", type="primary", use_container_width=True)

    with col2:
        preview_button = st.button("👁️ 预览条件", use_container_width=True)

    # 预览策略条件
    if preview_button:
        with st.expander("🔍 策略条件预览", expanded=True):
            try:
                params = json.loads(strategy_info['params_json'])
                st.markdown("**参数配置**:")

                for param_name, param_value in params.items():
                    st.markdown(f"- **{param_name}**: {param_value}")

                st.markdown("---")

                # 生成SQL条件
                sql_condition = generate_strategy_sql(strategy_info, params)
                st.markdown("**生成的SQL条件**:")
                st.code(sql_condition, language="sql")

            except Exception as e:
                st.error(f"解析策略失败: {e}")

    # 执行选股
    if execute_button:
        with st.spinner("正在执行选股..."):
            start_time = time.time()

            # 确定股票列表
            if selected_pool == "全部":
                stock_list = stocks['ts_code'].tolist()
            else:
                stock_list = stocks[stocks['pool_name'] == selected_pool]['ts_code'].tolist()

            # 执行选股
            results = execute_strategy(
                strategy_info,
                stock_list,
                execute_date.strftime("%Y-%m-%d")
            )

            elapsed_time = time.time() - start_time

        # 显示结果
        st.markdown("---")
        st.subheader("📊 选股结果")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("候选股票", len(stock_list))

        with col2:
            if results is not None:
                st.metric("选出股票", len(results))
            else:
                st.metric("选出股票", 0)

        with col3:
            if results is not None and len(results) > 0:
                rate = len(results) / len(stock_list) * 100
                st.metric("选出率", f"{rate:.2f}%")
            else:
                st.metric("选出率", "0%")

        st.metric("执行耗时", f"{elapsed_time:.2f}秒")

        st.markdown("---")

        # 显示选出的股票
        if results is not None and len(results) > 0:
            st.success(f"✅ 找到 {len(results)} 只符合条件的股票！")

            # 结果表格
            display_columns = ['ts_code', 'stock_name', 'close', 'change_pct', 'volume']

            # 添加指标列
            if 'ma5' in results.columns:
                display_columns.extend(['ma5', 'ma20'])

            if 'macd' in results.columns:
                display_columns.append('macd')

            if 'rsi6' in results.columns:
                display_columns.append('rsi6')

            # 确保列存在
            display_columns = [col for col in display_columns if col in results.columns]

            st.dataframe(
                results[display_columns],
                column_config={
                    "ts_code": "代码",
                    "stock_name": "名称",
                    "close": st.column_config.NumberColumn("收盘价", format="%.2f"),
                    "change_pct": st.column_config.NumberColumn("涨跌幅(%)", format="%.2f"),
                    "volume": st.column_config.NumberColumn("成交量", format="%.0f"),
                    "ma5": st.column_config.NumberColumn("MA5", format="%.2f"),
                    "ma20": st.column_config.NumberColumn("MA20", format="%.2f"),
                    "macd": st.column_config.NumberColumn("MACD", format="%.4f"),
                    "rsi6": st.column_config.NumberColumn("RSI6", format="%.2f")
                },
                use_container_width=True
            )

            # 导出按钮
            csv = results[display_columns].to_csv(index=False).encode('utf-8')
            col1, col2 = st.columns(2)

            with col1:
                st.download_button(
                    "📥 导出CSV",
                    csv,
                    f"selection_{selected_strategy}_{execute_date}.csv",
                    "text/csv",
                    use_container_width=True
                )

            with col2:
                if st.button("💾 保存到历史", use_container_width=True):
                    save_selection_to_history(
                        strategy_info['id'],
                        selected_strategy,
                        execute_date.strftime("%Y-%m-%d"),
                        selected_pool,
                        results,
                        elapsed_time
                    )
                    st.success("✅ 已保存到历史记录")

        else:
            st.warning("⚠️ 没有找到符合条件的股票")
            st.info("💡 建议:")
            st.info("- 检查策略参数是否过于严格")
            st.info("- 尝试扩大选股范围")
            st.info("- 更新数据后重新执行")


# ============ 历史记录 ============

def render_selection_history():
    """渲染选股历史页面"""

    st.subheader("选股历史")

    # 获取历史记录
    history = get_selection_history()

    if history is None or len(history) == 0:
        st.info("📭 暂无选股历史记录")
        return

    # 统计信息
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("总记录数", len(history))

    with col2:
        total_stocks = history['result_count'].sum()
        st.metric("累计选出", total_stocks)

    with col3:
        avg_count = history['result_count'].mean()
        st.metric("平均选出", f"{avg_count:.1f}")

    st.markdown("---")

    # 历史列表
    for _, record in history.iterrows():
        with st.expander(f"📅 {record['execute_date']} - {record['strategy_name']} ({record['result_count']}只)", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**股票池**: {record['stock_pool']}")

            with col2:
                st.markdown(f"**执行耗时**: {record['execution_time']:.2f}秒")

            with col3:
                st.markdown(f"**执行时间**: {record['created_at']}")

            # 查看详情按钮
            if st.button(f"查看详情", key=f"view_{record['id']}"):
                try:
                    results = json.loads(record['results_json'])
                    df = pd.DataFrame(results)

                    st.dataframe(df, use_container_width=True)

                    # 导出按钮
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        f"📥 导出_{record['id']}",
                        csv,
                        f"selection_{record['id']}.csv",
                        "text/csv"
                    )

                except Exception as e:
                    st.error(f"加载详情失败: {e}")

            # 删除按钮
            if st.button(f"🗑️ 删除", key=f"delete_{record['id']}", type="secondary"):
                delete_selection_history(record['id'])
                st.success("✅ 已删除")
                st.rerun()


# ============ 结果对比 ============

def render_result_comparison():
    """渲染结果对比页面"""

    st.subheader("策略对比")

    # 获取历史记录
    history = get_selection_history(limit=50)

    if history is None or len(history) == 0:
        st.info("📭 暂无历史记录可对比")
        return

    # 选择对比记录
    st.markdown("### 选择要对比的记录")

    recent_history = history.head(10)

    selected_ids = st.multiselect(
        "选择历史记录",
        options=recent_history['id'].tolist(),
        format_func=lambda x: f"{recent_history[recent_history['id']==x]['execute_date'].values[0]} - {recent_history[recent_history['id']==x]['strategy_name'].values[0]} ({recent_history[recent_history['id']==x]['result_count'].values[0]}只)",
        default=[]
    )

    if len(selected_ids) < 2:
        st.info("💡 请至少选择2条记录进行对比")
        return

    # 加载选中记录的结果
    comparison_data = []

    for record_id in selected_ids:
        record = history[history['id'] == record_id].iloc[0]

        try:
            results = json.loads(record['results_json'])
            df = pd.DataFrame(results)
            df['strategy'] = record['strategy_name']
            df['date'] = record['execute_date']

            comparison_data.append(df)

        except Exception as e:
            st.error(f"加载记录 {record_id} 失败: {e}")

    if comparison_data:
        # 合并数据
        combined = pd.concat(comparison_data, ignore_index=True)

        # 显示对比
        st.markdown("### 📊 对比结果")

        # 统计对比
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("对比记录数", len(selected_ids))

        with col2:
            unique_stocks = combined['ts_code'].nunique()
            st.metric("涉及股票", unique_stocks)

        with col3:
            total_selected = len(combined)
            st.metric("总选股数", total_selected)

        # 股票出现次数
        stock_counts = combined['ts_code'].value_counts()

        st.markdown("#### 🏆 多次被选中的股票")

        if len(stock_counts) > 0:
            top_stocks = stock_counts.head(10)

            for stock, count in top_stocks.items():
                stock_name = combined[combined['ts_code'] == stock]['stock_name'].iloc[0]
                st.metric(f"{stock} - {stock_name}", f"被选中 {count} 次")

        # 详细数据表
        st.markdown("#### 📋 详细对比表")

        st.dataframe(
            combined[['ts_code', 'stock_name', 'strategy', 'date', 'close', 'change_pct']],
            use_container_width=True
        )


# ============ 辅助函数 ============

def get_user_strategies():
    """获取用户策略"""
    try:
        sql = """
            SELECT id, strategy_name, strategy_type, template_name,
                   params_json, description
            FROM user_strategies
            WHERE is_active = 1
            ORDER BY created_at DESC
        """

        results = execute_query(sql, fetch_all=True)

        if results:
            columns = ['id', 'strategy_name', 'strategy_type', 'template_name', 'params_json', 'description']
            return pd.DataFrame(results, columns=columns)
        return pd.DataFrame()

    except Exception as e:
        st.error(f"获取策略失败: {e}")
        return pd.DataFrame()


def execute_strategy(strategy, stock_list, date):
    """执行选股策略"""

    try:
        # 解析策略参数
        params = json.loads(strategy['params_json'])
        template_name = strategy['template_name']

        # 生成SQL查询和参数
        sql, query_params = generate_strategy_sql(strategy, params, stock_list, date)

        # 执行查询
        with get_db_connection() as conn:
            df = pd.read_sql_query(sql, conn, params=query_params)

        return df if len(df) > 0 else None

    except Exception as e:
        st.error(f"执行策略失败: {e}")
        return None


def generate_strategy_sql(strategy, params, stock_list=None, date=None):
    """
    生成策略SQL查询

    参数:
        strategy: 策略信息字典，必须包含 'template_name' 键
        params: 参数字典（参数名到参数值的映射）
        stock_list: 可选，股票代码列表
        date: 可选，交易日期

    返回:
        tuple: (sql_query, param_list)
            - sql_query: 完整的SQL查询语句
            - param_list: 参数值列表（用于SQL的?占位符）
    """
    from utils.sql_builder import SQLBuilder
    from utils.field_mapper import get_all_direct_fields
    import os
    import json

    # 1. 加载策略模板
    template_name = strategy.get('template_name', '')
    if not template_name:
        raise ValueError("策略信息中缺少 'template_name' 字段")

    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'templates',
        'strategy_templates.json'
    )

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)
    except Exception as e:
        raise ValueError(f"加载策略模板失败: {e}")

    # 2. 查找匹配的模板
    template = None
    for strategy_type in templates.values():
        if isinstance(strategy_type, dict) and template_name in strategy_type:
            template = strategy_type[template_name]
            break

    if not template:
        raise ValueError(f"未找到策略模板: {template_name}")

    # 3. 获取SQL条件模板
    sql_condition_template = template.get('SQL条件', '')
    if not sql_condition_template:
        raise ValueError(f"策略 '{template_name}' 没有定义SQL条件")

    # 4. 使用SQLBuilder构建WHERE条件
    builder = SQLBuilder()
    where_clause, condition_params = builder.build_condition(sql_condition_template, params)

    # 5. 获取需要的字段
    required_fields = builder.get_required_fields(sql_condition_template, params)

    # 6. 构建基础查询
    # 基础字段（始终包含）
    base_fields = ['h.ts_code', 'p.stock_name', 'h.close', 'h.volume', 'i.change_pct']

    # 根据需要添加指标字段
    indicator_fields = []
    for field in required_fields:
        # 确定字段来自哪个表
        if field in ('close', 'open', 'high', 'low', 'volume', 'amount', 'turnover_ratio'):
            indicator_fields.append(f'h.{field}')
        else:
            indicator_fields.append(f'i.{field}')

    # 常用指标字段（始终包含以便展示）
    common_indicators = [
        'i.ma5', 'i.ma10', 'i.ma20', 'i.ma60',
        'i.dif', 'i.dea', 'i.macd',
        'i.k', 'i.d', 'i.j',
        'i.rsi6', 'i.rsi12', 'i.rsi24',
        'i.boll_upper', 'i.boll_mid', 'i.boll_lower'
    ]

    # 去重并合并字段
    all_fields = base_fields + list(set(indicator_fields + common_indicators))
    select_fields = ',\n            '.join(all_fields)

    sql = f"""
        SELECT DISTINCT
            {select_fields}
        FROM stock_daily_history h
        JOIN stock_indicators i ON h.ts_code = i.ts_code AND h.trade_date = i.trade_date
        LEFT JOIN stock_pool p ON h.ts_code = p.ts_code
        WHERE 1=1
    """

    query_params = []

    # 7. 添加日期过滤
    if date:
        sql += " AND DATE(h.trade_date) = ?"
        query_params.append(date)

    # 8. 添加股票池限制
    if stock_list:
        placeholders = ','.join(['?' for _ in stock_list])
        sql += f" AND h.ts_code IN ({placeholders})"
        query_params.extend(stock_list)

    # 9. 添加基本条件
    sql += " AND h.close IS NOT NULL"

    # 10. 添加策略条件
    if where_clause and where_clause != "1=1":
        sql += f" AND ({where_clause})"

    # 11. 合并参数列表（日期参数在前，然后是条件参数）
    query_params.extend(condition_params)

    # 12. 添加排序
    sql += " ORDER BY h.volume DESC"

    return sql, query_params


def save_selection_to_history(strategy_id, strategy_name, date, pool, results, elapsed_time):
    """保存选股结果到历史"""

    try:
        data = {
            'strategy_id': strategy_id,
            'strategy_name': strategy_name,
            'execute_date': date,
            'stock_pool': pool,
            'result_count': len(results) if results is not None else 0,
            'results_json': json.dumps(results.to_dict('records'), ensure_ascii=False) if results is not None else None,
            'execution_time': elapsed_time
        }

        execute_insert('selection_history', data)
        return True

    except Exception as e:
        st.error(f"保存历史失败: {e}")
        return False


def get_selection_history(limit=100):
    """获取选股历史"""
    try:
        sql = """
            SELECT id, strategy_id, strategy_name, execute_date,
                   stock_pool, result_count, execution_time, created_at
            FROM selection_history
            ORDER BY created_at DESC
            LIMIT ?
        """

        results = execute_query(sql, [limit], fetch_all=True)

        if results:
            columns = ['id', 'strategy_id', 'strategy_name', 'execute_date',
                      'stock_pool', 'result_count', 'execution_time', 'created_at']
            return pd.DataFrame(results, columns=columns)
        return pd.DataFrame()

    except Exception as e:
        st.error(f"获取历史失败: {e}")
        return pd.DataFrame()


def delete_selection_history(record_id):
    """删除历史记录"""
    try:
        sql = "DELETE FROM selection_history WHERE id = ?"
        with get_db_connection() as conn:
            conn.execute(sql, [record_id])
            conn.commit()
        return True

    except Exception as e:
        st.error(f"删除失败: {e}")
        return False
