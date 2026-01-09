# -*- coding: utf-8 -*-
"""
实时监控模块
提供股票价格和技术指标监控功能
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.db_helper import execute_query, execute_insert, get_db_connection


def render():
    """渲染实时监控页面"""
    st.title("🔔 实时监控")

    # 创建标签页
    tab1, tab2, tab3 = st.tabs([
        "➕ 创建监控",
        "📋 监控列表",
        "🔔 提醒历史"
    ])

    with tab1:
        render_create_monitor()

    with tab2:
        render_monitor_list()

    with tab3:
        render_alert_history()


# ============ 创建监控 ============

def render_create_monitor():
    """渲染创建监控页面"""

    st.subheader("创建监控任务")

    # 获取股票池
    from modules.data_manager import get_stock_pool
    stocks = get_stock_pool()

    if stocks is None or len(stocks) == 0:
        st.warning("⚠️ 股票池为空，请先在数据管理中添加股票")
        return

    col1, col2 = st.columns(2)

    with col1:
        # 选择股票
        selected_stock = st.selectbox(
            "选择股票",
            options=stocks['ts_code'].tolist(),
            format_func=lambda x: f"{x} - {stocks[stocks['ts_code']==x]['stock_name'].values[0] if stocks[stocks['ts_code']==x]['stock_name'].values[0] else '未知'}",
            key="monitor_stock"
        )

    with col2:
        # 任务名称
        task_name = st.text_input(
            "任务名称",
            value=f"监控_{selected_stock}",
            help="为这个监控任务起个名字"
        )

    st.markdown("---")

    # 监控条件
    st.markdown("### ⚙️ 监控条件")

    condition_type = st.selectbox(
        "条件类型",
        options=[
            "价格突破",
            "价格跌破",
            "涨跌幅监控",
            "成交量异常",
            "MACD金叉",
            "MACD死叉",
            "KDJ超卖",
            "KDJ超买",
            "RSI超卖",
            "RSI超买"
        ]
    )

    # 根据条件类型显示不同的参数设置
    condition_value = None
    condition_json = {}

    if condition_type in ["价格突破", "价格跌破"]:
        condition_value = st.number_input(
            "目标价格",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            help="触发警报的价格"
        )

    elif condition_type == "涨跌幅监控":
        col1, col2 = st.columns(2)

        with col1:
            threshold = st.number_input(
                "涨跌幅阈值(%)",
                min_value=-20.0,
                max_value=20.0,
                step=0.1,
                format="%.1f"
            )

        with col2:
            direction = st.selectbox(
                "方向",
                options=["上涨超过", "下跌超过"]
            )

        condition_value = threshold
        condition_json = {"direction": direction}

    elif condition_type == "成交量异常":
        condition_value = st.number_input(
            "量比倍数",
            min_value=1.0,
            max_value=10.0,
            step=0.1,
            value=2.0,
            help="成交量大于均线的倍数"
        )

    else:
        # 技术指标条件
        st.info(f"💡 {condition_type}：当指标出现信号时触发提醒")

    st.markdown("---")

    # 高级选项
    with st.expander("⚙️ 高级选项"):
        col1, col2 = st.columns(2)

        with col1:
            check_interval = st.number_input(
                "检查频率（分钟）",
                min_value=1,
                max_value=60,
                value=5,
                help="每隔多少分钟检查一次"
            )

        with col2:
            auto_refresh = st.checkbox(
                "自动刷新",
                value=True,
                help="是否自动刷新监控状态"
            )

    # 创建按钮
    if st.button("➕ 创建监控任务", type="primary", use_container_width=True):
        if task_name and selected_stock:
            success = create_monitor_task(
                task_name,
                selected_stock,
                condition_type,
                condition_value,
                condition_json
            )

            if success:
                st.success(f"✅ 监控任务 '{task_name}' 已创建！")
                st.info('💡 前往"监控列表"查看监控状态')
            else:
                st.error("❌ 创建失败")
        else:
            st.warning("⚠️ 请填写任务名称并选择股票")


# ============ 监控列表 ============

def render_monitor_list():
    """渲染监控列表页面"""

    st.subheader("监控任务列表")

    # 获取监控任务
    monitors = get_monitor_tasks()

    if monitors is None or len(monitors) == 0:
        st.info('📭 暂无监控任务，前往"创建监控"添加任务')
        return

    # 统计信息
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("总任务数", len(monitors))

    with col2:
        active_count = len(monitors[monitors['is_active'] == 1])
        st.metric("运行中", active_count)

    with col3:
        total_triggered = monitors['triggered_count'].sum()
        st.metric("累计触发", total_triggered)

    with col4:
        st.metric("今日触发", 0)  # TODO: 实现今日触发统计

    st.markdown("---")

    # 自动刷新开关
    col1, col2 = st.columns(2)

    with col1:
        auto_refresh = st.checkbox("🔄 自动刷新", value=False)

    with col2:
        if auto_refresh:
            refresh_interval = st.number_input("刷新间隔（秒）", min_value=5, max_value=60, value=10)

    # 显示监控任务
    for _, monitor in monitors.iterrows():
        with st.expander(f"🔔 {monitor['task_name']} - {monitor['stock_code']}", expanded=False):
            # 任务信息
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                status_color = "🟢" if monitor['is_active'] else "🔴"
                status_text = "运行中" if monitor['is_active'] else "已停止"
                st.markdown(f"**状态**: {status_color} {status_text}")

            with col2:
                st.markdown(f"**条件**: {monitor['condition_type']}")

            with col3:
                if monitor['condition_value']:
                    st.markdown(f"**阈值**: {monitor['condition_value']}")
                else:
                    st.markdown(f"**阈值**: -")

            with col4:
                st.markdown(f"**触发次数**: {monitor['triggered_count']}")

            # 最后检查时间
            if monitor['last_check_time']:
                last_check = pd.to_datetime(monitor['last_check_time'])
                time_diff = datetime.now() - last_check
                st.caption(f"最后检查: {time_diff.seconds // 60} 分钟前")

            # 实时状态
            if monitor['is_active']:
                with st.spinner("检查中..."):
                    status = check_monitor_status(monitor)

                    if status:
                        st.success(f"✅ {status['message']}")
                    else:
                        st.warning(status['message'] if isinstance(status, dict) else "检查中...")

            # 操作按钮
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                new_status = not monitor['is_active']
                action = "停止" if new_status else "启动"
                if st.button(f"{action}", key=f"toggle_monitor_{monitor['id']}", use_container_width=True):
                    toggle_monitor_status(monitor['id'], new_status)
                    st.rerun()

            with col2:
                if st.button("🔄 立即检查", key=f"check_{monitor['id']}", use_container_width=True):
                    result = check_monitor_task(monitor)
                    if result['triggered']:
                        st.success(f"🔔 {result['message']}")
                    else:
                        st.info(f"ℹ️ {result['message']}")

            with col3:
                if st.button("📝 编辑", key=f"edit_monitor_{monitor['id']}", use_container_width=True):
                    st.session_state[f"edit_monitor_{monitor['id']}"] = True
                    st.rerun()

            with col4:
                if st.button("🗑️ 删除", key=f"delete_monitor_{monitor['id']}", type="secondary", use_container_width=True):
                    if st.session_state.get(f'confirm_delete_monitor_{monitor["id"]}', False):
                        delete_monitor_task(monitor['id'])
                        st.success("✅ 已删除")
                        st.rerun()
                    else:
                        st.session_state[f'confirm_delete_monitor_{monitor["id"]}'] = True
                        st.warning("⚠️ 再次点击确认删除")

    # 自动刷新
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


# ============ 提醒历史 ============

def render_alert_history():
    """渲染提醒历史页面"""

    st.subheader("提醒历史")

    # 获取提醒历史
    alerts = get_alert_history(limit=100)

    if alerts is None or len(alerts) == 0:
        st.info("📭 暂无提醒记录")
        return

    # 统计信息
    col1, col2, col3 = st.columns(3)

    with col1:
        total_alerts = len(alerts)
        st.metric("总提醒数", total_alerts)

    with col2:
        unread_count = len(alerts[alerts['is_read'] == 0])
        st.metric("未读", unread_count)

    with col3:
        # 统计今日提醒
        today = datetime.now().date()
        today_alerts = alerts[pd.to_datetime(alerts['triggered_at']).dt.date == today]
        st.metric("今日提醒", len(today_alerts))

    st.markdown("---")

    # 过滤器
    col1, col2, col3 = st.columns(3)

    with col1:
        stock_filter = st.multiselect(
            "筛选股票",
            options=alerts['stock_code'].unique().tolist(),
            default=[],
            help="选择要查看的股票"
        )

    with col2:
        read_filter = st.selectbox(
            "阅读状态",
            options=["全部", "未读", "已读"]
        )

    with col3:
        if st.button("✅ 全部标为已读", use_container_width=True):
            mark_all_alerts_read()
            st.success("✅ 已全部标记为已读")
            st.rerun()

    st.markdown("---")

    # 过滤数据
    filtered_alerts = alerts.copy()

    if stock_filter:
        filtered_alerts = filtered_alerts[filtered_alerts['stock_code'].isin(stock_filter)]

    if read_filter == "未读":
        filtered_alerts = filtered_alerts[filtered_alerts['is_read'] == 0]
    elif read_filter == "已读":
        filtered_alerts = filtered_alerts[filtered_alerts['is_read'] == 1]

    # 按时间倒序
    filtered_alerts = filtered_alerts.sort_values('triggered_at', ascending=False)

    # 显示提醒列表
    for _, alert in filtered_alerts.iterrows():
        # 创建容器
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                # 时间和股票
                trigger_time = pd.to_datetime(alert['triggered_at'])
                time_str = trigger_time.strftime("%Y-%m-%d %H:%M:%S")

                if alert['is_read']:
                    st.markdown(f"📬 **{alert['stock_code']}** - {time_str}")
                else:
                    st.markdown(f"🔔 **{alert['stock_code']}** - {time_str}")

                # 提醒消息
                st.info(alert['trigger_message'])

            with col2:
                if not alert['is_read']:
                    if st.button("标记已读", key=f"read_{alert['id']}", use_container_width=True):
                        mark_alert_read(alert['id'])
                        st.rerun()

            st.markdown("---")


# ============ 辅助函数 ============

def create_monitor_task(task_name, stock_code, condition_type, condition_value=None, condition_json=None):
    """创建监控任务"""
    try:
        import json
        data = {
            'task_name': task_name,
            'stock_code': stock_code,
            'condition_type': condition_type,
            'condition_value': float(condition_value) if condition_value else None,
            'condition_json': json.dumps(condition_json, ensure_ascii=False) if condition_json else None,
            'is_active': 1
        }

        execute_insert('monitor_tasks', data)
        return True

    except Exception as e:
        st.error(f"创建任务失败: {e}")
        return False


def get_monitor_tasks(active_only=True):
    """获取监控任务列表"""
    try:
        sql = "SELECT * FROM monitor_tasks"

        if active_only:
            sql += " WHERE is_active = 1"

        sql += " ORDER BY created_at DESC"

        results = execute_query(sql, fetch_all=True)

        if results:
            columns = [
                'id', 'task_name', 'stock_code', 'condition_type', 'condition_value',
                'condition_json', 'is_active', 'last_check_time', 'triggered_count', 'created_at'
            ]
            return pd.DataFrame(results, columns=columns)
        return pd.DataFrame()

    except Exception as e:
        st.error(f"获取任务失败: {e}")
        return pd.DataFrame()


def check_monitor_status(monitor):
    """检查监控状态"""
    try:
        # 获取最新数据
        sql = """
            SELECT h.close, h.volume, i.ma5, i.ma20,
                   i.dif, i.dea, i.macd,
                   i.k, i.d, i.j,
                   i.rsi6
            FROM stock_daily_history h
            LEFT JOIN stock_indicators i ON h.ts_code = i.ts_code AND h.trade_date = i.trade_date
            WHERE h.ts_code = ?
            ORDER BY h.trade_date DESC
            LIMIT 2
        """

        results = execute_query(sql, [monitor['stock_code']], fetch_all=True)

        if not results or len(results) == 0:
            return {"status": "no_data", "message": "暂无数据"}

        # 检查条件
        triggered = False
        message = "未触发"

        latest = results[0]

        if monitor['condition_type'] == "价格突破":
            target = float(monitor['condition_value'])
            current = float(latest['close'])
            if current > target:
                triggered = True
                message = f"价格 {current:.2f} 突破 {target:.2f}"

        elif monitor['condition_type'] == "价格跌破":
            target = float(monitor['condition_value'])
            current = float(latest['close'])
            if current < target:
                triggered = True
                message = f"价格 {current:.2f} 跌破 {target:.2f}"

        elif monitor['condition_type'] == "涨跌幅监控":
            threshold = float(monitor['condition_value'])
            change_pct = float(latest.get('change_pct', 0))
            # TODO: 实现涨跌幅监控逻辑

        elif monitor['condition_type'] == "成交量异常":
            ratio = float(monitor['condition_value'])
            # TODO: 实现成交量监控逻辑

        elif monitor['condition_type'] in ["MACD金叉", "MACD死叉"]:
            dif = float(latest.get('dif', 0)) if latest.get('dif') else None
            dea = float(latest.get('dea', 0)) if latest.get('dea') else None

            if dif and dea:
                if monitor['condition_type'] == "MACD金叉" and dif > dea:
                    # 检查前一日是否也金叉（避免重复触发）
                    if len(results) > 1:
                        prev = results[1]
                        prev_dif = float(prev.get('dif', 0)) if prev.get('dif') else None
                        prev_dea = float(prev.get('dea', 0)) if prev.get('dea') else None
                        if prev_dif and prev_dea and prev_dif <= prev_dea:
                            triggered = True
                            message = f"MACD金叉 DIF:{dif:.4f} DEA:{dea:.4f}"

        elif monitor['condition_type'] == "KDJ超卖":
            k = float(latest.get('k', 0)) if latest.get('k') else None
            if k and k < 20:
                triggered = True
                message = f"KDJ超卖 K:{k:.2f}"

        elif monitor['condition_type'] == "KDJ超买":
            k = float(latest.get('k', 0)) if latest.get('k') else None
            if k and k > 80:
                triggered = True
                message = f"KDJ超买 K:{k:.2f}"

        elif monitor['condition_type'] == "RSI超卖":
            rsi = float(latest.get('rsi6', 0)) if latest.get('rsi6') else None
            if rsi and rsi < 30:
                triggered = True
                message = f"RSI超卖 RSI:{rsi:.2f}"

        elif monitor['condition_type'] == "RSI超买":
            rsi = float(latest.get('rsi6', 0)) if latest.get('rsi6') else None
            if rsi and rsi > 70:
                triggered = True
                message = f"RSI超买 RSI:{rsi:.2f}"

        # 如果触发，创建提醒
        if triggered:
            create_alert(
                monitor['id'],
                monitor['stock_code'],
                message
            )

            # 更新触发次数
            update_trigger_count(monitor['id'])

        return {"status": "ok", "triggered": triggered, "message": message}

    except Exception as e:
        return {"status": "error", "message": f"检查失败: {e}"}


def check_monitor_task(monitor):
    """立即检查监控任务"""
    return check_monitor_status(monitor)


def toggle_monitor_status(task_id, new_status):
    """切换监控任务状态"""
    try:
        sql = "UPDATE monitor_tasks SET is_active = ? WHERE id = ?"
        with get_db_connection() as conn:
            conn.execute(sql, [new_status, task_id])
            conn.commit()
        return True

    except Exception as e:
        st.error(f"更新失败: {e}")
        return False


def delete_monitor_task(task_id):
    """删除监控任务"""
    try:
        sql = "DELETE FROM monitor_tasks WHERE id = ?"
        with get_db_connection() as conn:
            conn.execute(sql, [task_id])
            conn.commit()
        return True

    except Exception as e:
        st.error(f"删除失败: {e}")
        return False


def create_alert(task_id, stock_code, message):
    """创建提醒"""
    try:
        data = {
            'task_id': task_id,
            'stock_code': stock_code,
            'trigger_message': message,
            'is_read': 0
        }

        execute_insert('monitor_alerts', data)
        return True

    except Exception as e:
        print(f"创建提醒失败: {e}")
        return False


def update_trigger_count(task_id):
    """更新触发次数"""
    try:
        sql = "UPDATE monitor_tasks SET triggered_count = triggered_count + 1, last_check_time = ? WHERE id = ?"
        with get_db_connection() as conn:
            conn.execute(sql, [datetime.now(), task_id])
            conn.commit()
        return True

    except Exception as e:
        return False


def get_alert_history(limit=100):
    """获取提醒历史"""
    try:
        sql = """
            SELECT a.*, m.task_name
            FROM monitor_alerts a
            LEFT JOIN monitor_tasks m ON a.task_id = m.id
            ORDER BY a.triggered_at DESC
            LIMIT ?
        """

        results = execute_query(sql, [limit], fetch_all=True)

        if results:
            columns = [
                'id', 'task_id', 'stock_code', 'triggered_at', 'trigger_message',
                'current_value', 'is_read', 'task_name'
            ]
            return pd.DataFrame(results, columns=columns)
        return pd.DataFrame()

    except Exception as e:
        st.error(f"获取历史失败: {e}")
        return pd.DataFrame()


def mark_alert_read(alert_id):
    """标记提醒为已读"""
    try:
        sql = "UPDATE monitor_alerts SET is_read = 1 WHERE id = ?"
        with get_db_connection() as conn:
            conn.execute(sql, [alert_id])
            conn.commit()
        return True

    except Exception as e:
        return False


def mark_all_alerts_read():
    """标记所有提醒为已读"""
    try:
        sql = "UPDATE monitor_alerts SET is_read = 1 WHERE is_read = 0"
        with get_db_connection() as conn:
            conn.execute(sql)
            conn.commit()
        return True

    except Exception as e:
        return False
