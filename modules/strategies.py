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

import config
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
        render_strategy_config()

    with tab2:
        render_my_strategies()

    with tab3:
        render_strategy_guide()


# ============ 策略配置 ============

def render_strategy_config():
    """渲染策略配置页面"""

    st.subheader("策略配置器")

    # 加载策略模板
    templates = load_strategy_templates()

    # 过滤出真正的策略类型（排除元数据键）
    metadata_keys = {'策略版本', '更新日期', 'version', 'update_date'}
    strategy_types = [k for k in templates.keys() if k not in metadata_keys]

    # 检查是否是编辑模式
    edit_mode = st.session_state.editing_strategy_id is not None
    edit_strategy_id = st.session_state.editing_strategy_id
    edit_strategy_data = None

    # 如果是编辑模式，获取策略数据
    if edit_mode:
        strategies = get_user_strategies()
        if strategies is not None and len(strategies) > 0:
            edit_strategy_data = strategies[strategies['id'] == int(edit_strategy_id)]
            if len(edit_strategy_data) == 0:
                # 策略不存在，清除编辑状态
                st.session_state.editing_strategy_id = None
                edit_mode = False
                edit_strategy_data = None

    # 选择策略类型
    col1, col2 = st.columns(2)

    with col1:
        strategy_type = st.selectbox(
            "策略类型",
            options=strategy_types,
            help="选择策略类型",
            index=0 if not edit_mode or edit_strategy_data is None or len(edit_strategy_data) == 0 else (strategy_types.index(edit_strategy_data.iloc[0]['strategy_type']) if edit_strategy_data.iloc[0]['strategy_type'] in strategy_types else 0)
        )

    with col2:
        # 确保 strategy_type 对应的值是字典
        if isinstance(templates[strategy_type], dict):
            strategies = list(templates[strategy_type].keys())
        else:
            st.error(f"策略类型 '{strategy_type}' 的数据格式错误")
            return

        # 如果是编辑模式，默认选中当前策略的模板
        default_strategy_idx = 0
        if edit_mode and edit_strategy_data is not None and len(edit_strategy_data) > 0:
            template_name = edit_strategy_data.iloc[0]['template_name']
            if template_name in strategies:
                default_strategy_idx = strategies.index(template_name)

        strategy_name = st.selectbox(
            "具体策略",
            options=strategies,
            index=default_strategy_idx
        )

    # 显示策略说明
    template = templates[strategy_type][strategy_name]

    st.markdown("---")
    if edit_mode:
        st.markdown("### ✏️ 编辑策略")
        st.info("💡 正在编辑策略，修改参数后点击「更新策略」保存，或点击「取消编辑」返回")
    else:
        st.markdown(f"### 📖 {strategy_name}")

    # 策略信息卡片
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"**适用场景**: {template['适用场景']}")

    with col2:
        risk_colors = {"低": "🟢", "中": "🟡", "高": "🟠", "极高": "🔴"}
        st.markdown(f"**风险等级**: {risk_colors.get(template['风险等级'], '')} {template['风险等级']}")

    with col3:
        st.markdown(f"**策略说明**: {template['描述']}")

    st.markdown("---")

    # 参数配置
    st.markdown("### 🎛️ 参数配置")

    user_params = {}

    # 如果是编辑模式，加载原有参数
    if edit_mode and edit_strategy_data is not None and len(edit_strategy_data) > 0:
        try:
            user_params = json.loads(edit_strategy_data.iloc[0]['params_json'])
        except (json.JSONDecodeError, KeyError, TypeError):
            user_params = {}

    # 动态生成参数输入控件
    params = template['参数']

    # 两列布局显示参数
    param_names = list(params.keys())
    mid = len(param_names) // 2

    col1, col2 = st.columns(2)

    with col1:
        for param_name in param_names[:mid]:
            param_config = params[param_name]
            # 使用已有参数值作为默认值
            if param_name in user_params:
                param_config = param_config.copy()
                param_config['默认值'] = user_params[param_name]
            value = render_param_input(param_name, param_config)
            user_params[param_name] = value

    with col2:
        for param_name in param_names[mid:]:
            param_config = params[param_name]
            # 使用已有参数值作为默认值
            if param_name in user_params:
                param_config = param_config.copy()
                param_config['默认值'] = user_params[param_name]
            value = render_param_input(param_name, param_config)
            user_params[param_name] = value

    st.markdown("---")

    # 策略预览
    with st.expander("👁️ 策略预览", expanded=False):
        st.markdown("**生成的SQL条件:**")
        sql_condition = generate_sql_condition(strategy_name, template, user_params)
        st.code(sql_condition, language="sql")

    # 保存策略
    st.markdown("### 💾 保存策略")

    if edit_mode:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # 编辑模式：使用原名称
            default_name = ""
            default_desc = ""
            if edit_strategy_data is not None and len(edit_strategy_data) > 0:
                default_name = edit_strategy_data.iloc[0]['strategy_name']
                default_desc = edit_strategy_data.iloc[0].get('description', '')

            save_name = st.text_input(
                "策略名称",
                value=default_name,
                help="策略名称（不可修改）",
                disabled=True
            )

        with col2:
            save_description = st.text_input(
                "策略说明（可选）",
                value=default_desc,
                help="简单描述你的策略思路"
            )

        with col3:
            if st.button("💾 更新策略", type="primary"):
                success = update_strategy(
                    int(edit_strategy_id),
                    save_name,
                    strategy_type,
                    strategy_name,
                    user_params,
                    save_description
                )
                if success:
                    st.success(f"✅ 策略 '{save_name}' 已更新！")
                    # 清除编辑状态
                    clear_edit_state()
                    st.rerun()
                else:
                    st.error("❌ 更新失败")

        with col4:
            if st.button("❌ 取消编辑"):
                clear_edit_state()
                st.info("已取消编辑")
                st.rerun()

    else:
        col1, col2, col3 = st.columns(3)

        with col1:
            save_name = st.text_input(
                "策略名称",
                value=f"{strategy_name}_自定义",
                help="为你的策略起个名字"
            )

        with col2:
            save_description = st.text_input(
                "策略说明（可选）",
                value="",
                help="简单描述你的策略思路"
            )

        with col3:
            if st.button("💾 保存策略", type="primary"):
                if save_name:
                    # 检查是否已存在
                    if check_strategy_exists(save_name):
                        st.warning(f"⚠️ 策略 '{save_name}' 已存在，请使用其他名称")
                    else:
                        # 保存新策略
                        success = save_strategy(
                            save_name,
                            strategy_type,
                            strategy_name,
                            user_params,
                            save_description
                        )

                        if success:
                            st.success(f"✅ 策略 '{save_name}' 已保存！")
                        else:
                            st.error("❌ 保存失败")
                else:
                    st.warning("⚠️ 请输入策略名称")


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

            # 参数显示
            st.markdown("**参数配置**:")

            try:
                params = json.loads(strategy['params_json'])

                for param_name, param_value in params.items():
                    st.markdown(f"- **{param_name}**: {param_value}")

            except:
                st.warning("参数解析失败")

            st.markdown("---")

            # 操作按钮
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("📝 编辑", key=f"edit_{strategy['id']}"):
                    # 设置编辑状态
                    st.session_state.editing_strategy_id = strategy['id']
                    st.success(f"✅ 正在编辑策略: {strategy['strategy_name']}，请切换到「配置策略」标签页")
                    st.rerun()

            with col2:
                if st.button("📋 复制", key=f"copy_{strategy['id']}"):
                    copy_strategy(strategy['id'])
                    st.success("✅ 已复制")

            with col3:
                new_status = not strategy['is_active']
                action = "启用" if new_status else "禁用"
                if st.button(action, key=f"toggle_{strategy['id']}"):
                    toggle_strategy_status(strategy['id'], new_status)
                    st.rerun()

            with col4:
                if st.button("🗑️ 删除", key=f"delete_{strategy['id']}", type="secondary"):
                    if st.session_state.get(f'confirm_delete_{strategy["id"]}', False):
                        delete_strategy(strategy['id'])
                        st.success("✅ 已删除")
                        st.rerun()
                    else:
                        st.session_state[f'confirm_delete_{strategy["id"]}'] = True
                        st.warning("⚠️ 再次点击确认删除")


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

def load_strategy_templates():
    """加载策略模板"""
    try:
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates',
            'strategy_templates.json'
        )

        with open(template_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)

        return templates

    except Exception as e:
        st.error(f"加载策略模板失败: {e}")
        return {}


def render_param_input(param_name, param_config):
    """渲染参数输入控件"""

    param_type = param_config.get('类型', 'slider')
    default_value = param_config.get('默认值')
    min_value = param_config.get('最小值')
    max_value = param_config.get('最大值')
    label = param_config.get('标签', param_name)
    description = param_config.get('说明', '')

    if param_type == 'slider':
        # 判断是否需要使用浮点数
        is_float = any(isinstance(v, float) for v in [default_value, min_value, max_value] if v is not None)

        if is_float:
            value = st.slider(
                f"{label} {description}",
                min_value=float(min_value) if min_value is not None else 0.0,
                max_value=float(max_value) if max_value is not None else 100.0,
                value=float(default_value) if default_value is not None else 0.0,
                step=0.01,
                help=description
            )
        else:
            value = st.slider(
                f"{label} {description}",
                min_value=int(min_value) if min_value is not None else 0,
                max_value=int(max_value) if max_value is not None else 100,
                value=int(default_value) if default_value is not None else 0,
                step=1,
                help=description
            )

    elif param_type == 'checkbox':
        value = st.checkbox(
            label,
            value=bool(default_value),
            help=description
        )

    else:
        value = st.number_input(
            label,
            value=float(default_value),
            help=description
        )

    return value


def generate_sql_condition(strategy_name, template, user_params):
    """生成SQL查询条件"""

    # 这里是简化版本，实际应该根据参数生成SQL
    base_condition = template.get('SQL条件', '')

    # 替换参数占位符
    # TODO: 实现更智能的SQL生成逻辑

    return base_condition


def save_strategy(name, strategy_type, template_name, params, description=None):
    """保存策略到数据库"""
    try:
        data = {
            'user_id': 'default',
            'strategy_name': name,
            'strategy_type': strategy_type,
            'template_name': template_name,
            'params_json': json.dumps(params, ensure_ascii=False),
            'description': description
        }

        execute_insert('user_strategies', data)
        return True

    except Exception as e:
        st.error(f"保存失败: {e}")
        return False


def clear_edit_state():
    """清除所有编辑状态"""
    st.session_state.editing_strategy_id = None
    # 同时清除旧的编辑状态
    for key in list(st.session_state.keys()):
        if key.startswith('edit_strategy_'):
            del st.session_state[key]


def update_strategy(strategy_id, name, strategy_type, template_name, params, description=None):
    """更新策略"""
    try:
        from utils.db_helper import get_db_connection
        with get_db_connection() as conn:
            sql = """
                UPDATE user_strategies
                SET strategy_name = ?, strategy_type = ?, template_name = ?,
                    params_json = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            conn.execute(sql, [
                name, strategy_type, template_name,
                json.dumps(params, ensure_ascii=False), description, strategy_id
            ])
            conn.commit()
        return True

    except Exception as e:
        st.error(f"更新失败: {e}")
        return False


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


def check_strategy_exists(strategy_name):
    """检查策略是否已存在"""
    try:
        sql = "SELECT COUNT(*) as count FROM user_strategies WHERE strategy_name = ?"
        result = execute_query(sql, [strategy_name], fetch_one=True)
        return result['count'] > 0 if result else False

    except Exception as e:
        return False


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
