# -*- coding: utf-8 -*-
"""
策略配置模块
提供策略模板选择和参数配置功能
"""

import streamlit as st
import json
import pandas as pd
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_helper import execute_query, execute_insert, get_db_connection


def render():
    """渲染策略配置页面"""
    st.title("⚙️ 策略配置")

    # 初始化编辑状态
    if 'editing_strategy_id' not in st.session_state:
        st.session_state.editing_strategy_id = None

    # 创建标签页
    tab1, tab2, tab3 = st.tabs([
        "📝 配置策略",
        "💾 我的策略",
        "📋 策略说明"
    ])

    with tab1:
        render_strategy_config_v2()

    with tab2:
        render_my_strategies()

    with tab3:
        render_strategy_guide()


# ============ 策略配置（V2版本 - 使用模板引擎）============

def render_strategy_config_v2():
    """
    渲染策略配置页面（新版本 - 使用模板引擎）

    新版本特性：
    - 条件可选：用户可以选择需要的条件
    - 参数化：支持动态参数配置
    - SQL预览：实时预览生成的SQL
    """
    st.subheader("策略配置器")

    try:
        from utils.strategy_template_engine import StrategyTemplateEngine

        # 初始化引擎
        engine = StrategyTemplateEngine()

        # 获取所有策略分类
        all_strategies = engine.get_all_strategies_ui_config()

        # 选择策略类型和具体策略
        col1, col2 = st.columns(2)

        with col1:
            category = st.selectbox(
                "策略类型",
                options=list(all_strategies.keys()),
                help="选择策略类型",
                key="v2_category"
            )

        with col2:
            strategies_in_category = all_strategies[category]
            strategy_options = [f"{s['name']} ({s['id']})" for s in strategies_in_category]
            selected_display = st.selectbox(
                "具体策略",
                options=strategy_options,
                help="选择具体策略",
                key="v2_strategy_select"
            )

            # 从显示名称中提取 strategy_id
            strategy_id = selected_display.split('(')[-1].rstrip(')')

        # 获取策略配置
        strategy_config = engine.get_strategy_ui_config(strategy_id)

        # 显示策略信息
        st.markdown("---")
        st.markdown(f"### 📖 {strategy_config['name']}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.info(f"**适用场景**: {category}")

        with col2:
            risk_colors = {"低": "🟢", "中": "🟡", "高": "🟠"}
            st.markdown(f"**风险等级**: {risk_colors.get(strategy_config['risk_level'], '')} {strategy_config['risk_level']}")

        with col3:
            st.markdown(f"**组合逻辑**: {strategy_config['combine_logic']}")

        st.markdown(f"**策略说明**: {strategy_config['description']}")

        st.markdown("---")

        # 条件选择
        st.markdown("### 🎛️ 条件选择（可多选）")

        selected_conditions = []
        condition_params = {}

        for cond_config in strategy_config['conditions']:
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    # 条件选择复选框
                    is_selected = st.checkbox(
                        cond_config['label'],
                        value=cond_config['enabled'],
                        key=f"v2_cond_{cond_config['id']}",
                        help=f"ID: {cond_config['id']}"
                    )

                    if is_selected:
                        selected_conditions.append(cond_config['id'])

                        # 显示参数配置
                        if cond_config['params']:
                            with st.expander("配置参数", expanded=False):
                                for param_config in cond_config['params']:
                                    value = render_param_input_v2(param_config)
                                    condition_params[param_config['name']] = value

                with col2:
                    if cond_config['required']:
                        st.caption("⚠️ 必需")

        st.markdown("---")

        # SQL预览
        with st.expander("👁️ SQL预览", expanded=False):
            user_config = {
                'selected_conditions': selected_conditions,
                'params': condition_params
            }

            try:
                where_clause, params = engine.build_sql(strategy_id, user_config)

                st.markdown("**WHERE条件:**")
                st.code(f"WHERE {where_clause}", language="sql")

                if params:
                    st.markdown("**参数值:**")
                    for i, param in enumerate(params):
                        st.text(f"?{i+1} = {param}")

            except Exception as e:
                st.error(f"SQL生成失败: {e}")

        st.markdown("---")

        # 保存策略
        st.markdown("### 💾 保存策略")

        col1, col2, col3 = st.columns(3)

        with col1:
            save_name = st.text_input(
                "策略名称",
                value=f"{strategy_config['name']}_自定义",
                help="为你的策略起个名字",
                key="v2_save_name"
            )

        with col2:
            save_description = st.text_input(
                "策略说明（可选）",
                value="",
                help="简单描述你的策略思路",
                key="v2_save_description"
            )

        with col3:
            if st.button("💾 保存策略", type="primary", key="v2_save_button"):
                if save_name:
                    if check_strategy_exists_v2(save_name):
                        st.warning(f"⚠️ 策略 '{save_name}' 已存在，请使用其他名称")
                    else:
                        # 保存新格式策略
                        success = save_strategy_v2(
                            save_name,
                            strategy_id,
                            selected_conditions,
                            condition_params,
                            save_description
                        )

                        if success:
                            st.success(f"✅ 策略 '{save_name}' 已保存！")
                        else:
                            st.error("❌ 保存失败")
                else:
                    st.warning("⚠️ 请输入策略名称")

    except Exception as e:
        st.error(f"策略配置错误: {e}")
        st.exception(e)


def render_param_input_v2(param_config):
    """
    渲染参数输入控件（新版本）

    参数:
        param_config: 参数配置字典 {
            'name': 'volume_ratio',
            'label': '放量倍数',
            'type': 'float',
            'default': 2.0,
            'min': 1.5,
            'max': 5.0,
            'step': 0.1
        }

    返回:
        参数值
    """
    param_type = param_config['type']
    label = param_config['label']
    default = param_config['default']
    min_val = param_config.get('min')
    max_val = param_config.get('max')
    step = param_config.get('step')

    # 为每个参数生成唯一的 key
    param_key = f"v2_param_{param_config['name']}"

    if param_type == 'int':
        if min_val is not None and max_val is not None:
            return st.slider(
                label,
                min_value=int(min_val),
                max_value=int(max_val),
                value=int(default),
                step=int(step) if step else 1,
                key=param_key
            )
        else:
            return st.number_input(
                label,
                value=int(default),
                key=param_key
            )

    elif param_type == 'float':
        if min_val is not None and max_val is not None:
            return st.slider(
                label,
                min_value=float(min_val),
                max_value=float(max_val),
                value=float(default),
                step=float(step) if step else 0.01,
                key=param_key
            )
        else:
            return st.number_input(
                label,
                value=float(default),
                key=param_key
            )

    elif param_type == 'bool':
        return st.checkbox(
            label,
            value=bool(default),
            key=param_key
        )

    else:
        return st.text_input(
            label,
            value=str(default),
            key=param_key
        )


def save_strategy_v2(name, strategy_id, selected_conditions, params, description=None):
    """
    保存策略（V2版本 - 新格式）

    参数:
        name: 策略名称
        strategy_id: 策略模板ID
        selected_conditions: 选中的条件列表
        params: 参数字典
        description: 策略说明

    返回:
        bool: 是否成功
    """
    try:
        data = {
            'user_id': 'default',
            'strategy_name': name,
            'strategy_type': strategy_id,  # 使用 strategy_id 作为类型
            'template_name': 'template_v2',  # 标记为新版本
            'params_json': json.dumps({
                'strategy_id': strategy_id,
                'selected_conditions': selected_conditions,
                'params': params
            }, ensure_ascii=False),
            'description': description
        }

        execute_insert('user_strategies', data)
        return True

    except Exception as e:
        st.error(f"保存失败: {e}")
        return False


def check_strategy_exists_v2(strategy_name):
    """检查策略是否已存在（V2版本）"""
    try:
        sql = "SELECT COUNT(*) as count FROM user_strategies WHERE strategy_name = ?"
        result = execute_query(sql, [strategy_name], fetch_one=True)
        return result['count'] > 0 if result else False

    except Exception as e:
        return False


# ============ 我的策略 ============

def render_my_strategies():
    """渲染我的策略页面"""

    st.subheader("我的策略")

    # 获取用户策略
    strategies = get_user_strategies()

    if strategies is None or len(strategies) == 0:
        st.info("📭 你还没有保存任何策略，去配置一个吧！")
        return

    # 策略统计
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("策略总数", len(strategies))

    with col2:
        type_counts = strategies['strategy_type'].value_counts()
        st.metric("策略类型", len(type_counts))

    with col3:
        active_count = len(strategies[strategies['is_active'] == 1])
        st.metric("启用中", active_count)

    st.markdown("---")

    # 策略列表
    st.markdown("### 📋 策略列表")

    for _, strategy in strategies.iterrows():
        with st.expander(f"📌 {strategy['strategy_name']}", expanded=False):
            # 策略信息
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**类型**: {strategy['strategy_type']}")

            with col2:
                st.markdown(f"**模板**: {strategy['template_name']}")

            with col3:
                status = "✅ 启用" if strategy['is_active'] else "❌ 禁用"
                st.markdown(f"**状态**: {status}")

            if strategy['description']:
                st.markdown(f"**说明**: {strategy['description']}")

            st.markdown("---")

            # 操作按钮
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button(f"✏️ 编辑", key=f"edit_{strategy['id']}"):
                    st.session_state.editing_strategy_id = strategy['id']
                    st.rerun()

            with col2:
                new_status = not strategy['is_active']
                status_text = "禁用" if strategy['is_active'] else "启用"
                if st.button(f"{status_text}", key=f"toggle_{strategy['id']}"):
                    toggle_strategy_status(strategy['id'], new_status)
                    st.rerun()

            with col3:
                if st.button(f"📋 复制", key=f"copy_{strategy['id']}"):
                    if copy_strategy(strategy['id']):
                        st.success("✅ 已复制")
                        st.rerun()

            with col4:
                # 使用独立的标志键和按钮键
                confirm_key = f'show_confirm_{strategy["id"]}'
                if not st.session_state.get(confirm_key, False):
                    if st.button(f"🗑️ 删除", key=f"delete_btn_{strategy['id']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(f"⚠️ 确认", key=f"confirm_yes_{strategy['id']}", type="primary"):
                            delete_strategy(strategy['id'])
                            st.success("✅ 已删除")
                            st.rerun()
                    with col_b:
                        if st.button(f"❌ 取消", key=f"confirm_no_{strategy['id']}"):
                            st.session_state[confirm_key] = False
                            st.rerun()


# ============ 策略说明 ============

def render_strategy_guide():
    """渲染策略说明页面"""

    st.subheader("策略使用指南")

    st.markdown("""
    ## 📚 策略类型说明

    ### 📈 趋势型策略
    适合牛市或明确上升趋势的市场。

    **特点**:
    - 追随趋势，顺势而为
    - 在趋势确立后买入
    - 适合中长期持有

    **推荐使用**:
    - 市场整体上涨
    - 个股形成明确上升趋势
    - 成交量配合

    ### 🚀 突破型策略
    适合震荡市场，捕捉突破机会。

    **特点**:
    - 捕捉价格突破信号
    - 关注放量突破
    - 短期爆发力强

    **推荐使用**:
    - 横盘整理后突破
    - 放量确认突破
    - 设置止损

    ### 📉 震荡型策略
    适合熊市或震荡市场，做超跌反弹。

    **特点**:
    - 逆向思维，低买高卖
    - 关注超卖信号
    - 短期操作为主

    **推荐使用**:
    - 市场超跌
    - 技术指标极端
    - 快进快出

    ## ⚙️ 参数调整建议

    ### 激进型配置
    - 放宽条件限制
    - 提高触发概率
    - 风险较高，收益潜力大

    ### 保守型配置
    - 严格条件限制
    - 降低触发概率
    - 风险较低，胜率较高

    ## 💡 使用技巧

    1. **组合使用**: 不同市场环境使用不同类型策略
    2. **参数优化**: 根据历史数据回调优化参数
    3. **风险控制**: 严格执行止损，控制单只股票仓位
    4. **持续学习**: 观察策略表现，不断优化改进

    ## ⚠️ 注意事项

    - 策略不是万能的，没有100%胜率的策略
    - 历史表现不代表未来收益
    - 务必结合市场环境灵活运用
    - 严格控制风险，做好资金管理
    """)


# ============ 辅助函数 ============

def get_user_strategies(user_id='default'):
    """获取用户策略列表"""
    try:
        sql = """
            SELECT id, strategy_name, strategy_type, template_name,
                   params_json, description, is_active, created_at
            FROM user_strategies
            WHERE user_id = ?
            ORDER BY created_at DESC
        """

        results = execute_query(sql, [user_id], fetch_all=True)

        if results:
            columns = ['id', 'strategy_name', 'strategy_type', 'template_name',
                      'params_json', 'description', 'is_active', 'created_at']
            return pd.DataFrame(results, columns=columns)
        return pd.DataFrame()

    except Exception as e:
        st.error(f"获取策略列表失败: {e}")
        return pd.DataFrame()


def copy_strategy(strategy_id):
    """复制策略"""
    try:
        # 获取原策略
        sql = "SELECT * FROM user_strategies WHERE id = ?"
        result = execute_query(sql, [strategy_id], fetch_one=True)

        if result:
            # 创建新策略
            new_name = f"{result['strategy_name']}_副本"
            data = {
                'user_id': 'default',
                'strategy_name': new_name,
                'strategy_type': result['strategy_type'],
                'template_name': result['template_name'],
                'params_json': result['params_json'],
                'description': f"复制自: {result['strategy_name']}"
            }

            execute_insert('user_strategies', data)
            return True

        return False

    except Exception as e:
        st.error(f"复制失败: {e}")
        return False


def toggle_strategy_status(strategy_id, new_status):
    """切换策略状态"""
    try:
        sql = "UPDATE user_strategies SET is_active = ? WHERE id = ?"
        with get_db_connection() as conn:
            conn.execute(sql, [new_status, strategy_id])
            conn.commit()
        return True

    except Exception as e:
        st.error(f"更新失败: {e}")
        return False


def delete_strategy(strategy_id):
    """删除策略"""
    try:
        sql = "DELETE FROM user_strategies WHERE id = ?"
        with get_db_connection() as conn:
            conn.execute(sql, [strategy_id])
            conn.commit()
        return True

    except Exception as e:
        st.error(f"删除失败: {e}")
        return False
