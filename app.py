# -*- coding: utf-8 -*-
"""
股票量化选股系统 - 主应用入口
新手友好的Web界面，无需编程知识即可使用
"""

import streamlit as st
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

# ============ 页面配置 ============
st.set_page_config(
    page_title=config.STREAMLIT_TITLE,
    page_icon=config.STREAMLIT_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ 自定义CSS样式 ============
st.markdown("""
<style>
    /* 主标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* 卡片样式 */
    .info-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

    /* 成功消息样式 */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }

    /* 警告消息样式 */
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }

    /* 错误消息样式 */
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============ 会话状态初始化 ============
def init_session_state():
    """初始化会话状态变量"""
    if 'page' not in st.session_state:
        st.session_state.page = '📊 数据管理'

    if 'user_id' not in st.session_state:
        st.session_state.user_id = 'default'

    if 'first_run' not in st.session_state:
        st.session_state.first_run = True

    if 'show_tutorial' not in st.session_state:
        st.session_state.show_tutorial = False


# ============ 页面渲染函数 ============

def render_home():
    """渲染首页/欢迎页面"""
    st.markdown('<div class="main-title">📈 股票量化选股系统</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 功能介绍
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
        ### 📊 数据管理
        - 自动下载股票数据
        - 支持多周期数据
        - 增量更新功能
        """)

    with col2:
        st.success("""
        ### ⚙️ 策略配置
        - 16种经典策略
        - 可视化参数调整
        - 保存自定义策略
        """)

    with col3:
        st.warning("""
        ### 🎯 智能选股
        - 一键执行选股
        - 结果可视化展示
        - 历史记录查询
        """)

    st.markdown("---")

    # 数据看板
    st.subheader("📊 数据看板")

    try:
        from utils.db_helper import get_db_info
        db_info = get_db_info()

        # 数据统计
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            history_count = db_info.get('stock_daily_history_count', 0)
            st.metric("日线数据", f"{history_count:,}")

        with col2:
            indicator_count = db_info.get('stock_indicators_count', 0)
            st.metric("指标数据", f"{indicator_count:,}")

        with col3:
            stock_count = db_info.get('stock_pool_count', 0)
            st.metric("股票池", stock_count)

        with col4:
            strategy_count = db_info.get('user_strategies_count', 0)
            st.metric("策略数量", strategy_count)

        with col5:
            selection_count = db_info.get('selection_history_count', 0)
            st.metric("选股记录", selection_count)

        st.markdown("---")

    except Exception as e:
        st.error(f"获取数据看板失败: {e}")

    # 快速开始指南
    st.subheader("🚀 快速开始（3步）")

    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown("""
        <div class="info-card">
            <h3>1️⃣ 下载数据</h3>
            <p>在"数据管理"页面下载你关注的股票数据</p>
        </div>
        """, unsafe_allow_html=True)

    with step2:
        st.markdown("""
        <div class="info-card">
            <h3>2️⃣ 配置策略</h3>
            <p>在"策略配置"页面选择或配置选股策略</p>
        </div>
        """, unsafe_allow_html=True)

    with step3:
        st.markdown("""
        <div class="info-card">
            <h3>3️⃣ 执行选股</h3>
            <p>在"执行选股"页面一键筛选符合条件的股票</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 系统状态
    st.subheader("📋 系统状态")

    try:
        from utils.db_helper import get_db_info
        db_info = get_db_info()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            status = "✅ 正常" if db_info['db_exists'] else "⚠️ 未初始化"
            st.metric("数据库状态", status)

        with col2:
            table_count = db_info.get('table_count', 0)
            st.metric("数据表数量", table_count)

        with col3:
            pool_count = db_info.get('stock_pool_count', 0)
            st.metric("股票池数量", pool_count)

        with col4:
            strategy_count = db_info.get('user_strategies_count', 0)
            st.metric("策略数量", strategy_count)

    except Exception as e:
        st.error(f"获取系统状态失败: {e}")


def render_data_manager():
    """渲染数据管理页面"""
    from modules import data_manager
    data_manager.render()


def render_indicators():
    """渲染技术指标页面"""
    from modules import indicators
    indicators.render()


def render_strategies():
    """渲染策略配置页面"""
    from modules import strategies
    strategies.render()


def render_selector():
    """渲染选股执行页面"""
    from modules import selector
    selector.render()


def render_screener():
    """渲染 parquet 选股器页面"""
    from modules import screener
    screener.render()


def render_monitor():
    """渲染实时监控页面"""
    from modules import monitor
    monitor.render()


def render_help():
    """渲染帮助文档页面"""
    st.title("📚 帮助文档")

    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📖 使用指南",
        "❓ 常见问题",
        "📊 技术指标说明",
        "⚙️ 策略原理",
        "🔧 故障排查"
    ])

    with tab1:
        render_user_guide()

    with tab2:
        render_faq()

    with tab3:
        render_indicators_guide()

    with tab4:
        render_strategy_guide()

    with tab5:
        render_troubleshooting()


def render_user_guide():
    """渲染用户指南"""
    st.markdown("""
    ## 📖 系统使用指南

    ### 快速开始（3步）

    #### 第1步：下载数据
    1. 点击左侧导航栏的 **"📊 数据管理"**
    2. 在 **"股票池管理"** 中添加股票代码（如：600519.SH）
    3. 切换到 **"数据下载"** 标签页
    4. 选择日期范围和周期，点击"开始下载"

    #### 第2步：配置策略
    1. 点击 **"⚙️ 策略配置"**
    2. 选择策略类型（趋势型/突破型/震荡型）
    3. 选择具体策略并调整参数
    4. 点击 **"💾 保存策略"**

    #### 第3步：执行选股
    1. 点击 **"🎯 执行选股"**
    2. 选择已保存的策略和股票池
    3. 点击 **"🎯 开始选股"**
    4. 查看结果并导出

    ---

    ### 功能模块介绍

    #### 📊 数据管理
    - **股票池管理**：添加、删除、分组管理股票
    - **数据下载**：下载历史数据（支持多周期）
    - **数据更新**：增量更新最新数据
    - **数据查询**：查看和导出数据

    #### 📈 技术指标
    - **指标计算**：自动计算MA、MACD、KDJ、RSI、BOLL等指标
    - **K线图表**：交互式K线图和指标图
    - **指标查询**：按股票、日期查询指标数据

    #### ⚙️ 策略配置
    - **策略模板**：16种经典策略模板
    - **参数配置**：可视化参数调整
    - **策略管理**：保存、编辑、复制、删除策略

    #### 🎯 执行选股
    - **策略执行**：一键执行选股
    - **结果展示**：表格展示选股结果
    - **历史记录**：查看和对比历史选股

    #### 🔔 实时监控
    - **监控设置**：设置价格和指标监控
    - **实时检查**：自动检查触发条件
    - **提醒功能**：触发时弹窗提醒
    """)


def render_faq():
    """渲染常见问题"""
    st.markdown("""
    ## ❓ 常见问题

    ### 基础问题

    **Q: 如何开始使用？**
    A: 新手建议按以下流程操作：
    1. 先在"数据管理"中添加几只股票并下载数据
    2. 在"策略配置"中选择一个简单策略（如均线多头排列）
    3. 在"执行选股"中运行策略
    4. 查看结果并导出

    **Q: 支持哪些股票？**
    A: 支持A股市场所有股票，包括：
    - 上海证券交易所：600xxx.SH、688xxx.SH（科创板）
    - 深圳证券交易所：000xxx.SZ、002xxx.SZ、300xxx.SZ（创业板）

    **Q: 数据从哪里来？**
    A: 数据来自baostock免费证券数据平台，数据准确可靠。

    **Q: 股票代码格式是什么？**
    A: 标准格式为：代码.市场
    - 上海市场：600519.SH（贵州茅台）
    - 深圳市场：000001.SZ（平安银行）

    ### 数据相关问题

    **Q: 支持哪些数据周期？**
    A: 支持5种周期：
    - 日线（d）：最常用，适合中长期分析
    - 60分钟（60m）：短线分析
    - 30分钟（30m）：短线分析
    - 15分钟（15m）：日内交易
    - 5分钟（5m）：日内交易

    **Q: 数据更新频率？**
    A:
    - 日线数据：每个交易日收盘后更新
    - 分钟数据：盘中数据可能有延迟
    - 建议每天收盘后执行一次增量更新

    **Q: 下载数据很慢怎么办？**
    A:
    - 首次下载建议先下载数量测试
    - 避开高峰时段（9:30-15:00）
    - 使用批量导入功能，一次性添加多只股票

    **Q: 数据缺失怎么办？**
    A:
    - 使用"数据更新"功能重新下载
    - 检查网络连接
    - 某些股票可能停牌，导致数据缺失

    ### 策略相关问题

    **Q: 如何选择合适的策略？**
    A: 根据市场环境选择：
    - **牛市/上升趋势**：使用趋势型策略（均线多头排列、MACD金叉）
    - **震荡市**：使用突破型策略（箱体突破、放量突破）
    - **熊市/下跌**：使用震荡型策略（KDJ低位金叉、RSI超卖）

    **Q: 策略参数如何调整？**
    A:
    - 保守型：严格条件，低风险（如RSI < 20）
    - 激进型：宽松条件，高收益潜力（如RSI < 30）
    - 建议先用默认值测试，再根据结果调整

    **Q: 为什么选股结果为空？**
    A: 可能原因：
    1. 策略条件过于严格
    2. 数据未更新或缺失
    3. 市场环境不适用该策略
    4. 股票池为空

    **Q: 选股结果准确吗？**
    A:
    - 结果基于历史数据和技术指标计算
    - 仅供参考，不构成投资建议
    - 需结合其他分析方法和市场环境
    - 股市有风险，投资需谨慎

    ### 技术问题

    **Q: 启动失败怎么办？**
    A: 检查：
    1. Python版本是否为3.10+
    2. 依赖包是否正确安装
    3. 端口8501是否被占用
    4. 查看错误日志

    **Q: 如何备份数据？**
    A:
    1. 备份 `data/stock_data.db` 数据库文件
    2. 导出重要的选股结果
    3. 导出策略配置

    **Q: 如何清空数据重新开始？**
    A:
    1. 关闭应用
    2. 删除 `data/stock_data.db` 文件
    3. 重新启动应用（会自动创建新数据库）

    **Q: 内存不足怎么办？**
    A:
    - 减少同时下载的股票数量
    - 缩短日期范围
    - 关闭其他占用内存的程序
    - 增加系统内存

    ### 其他问题

    **Q: 可以回测策略吗？**
    A: 当前版本不支持自动回测，建议：
    - 使用历史日期执行选股
    - 手动对比后续走势
    - 记录策略表现

    **Q: 可以支持实盘交易吗？**
    A: 不支持。本系统仅用于选股分析，不提供交易功能。

    **Q: 如何获取更多帮助？**
    A:
    1. 查看完整文档
    2. 查看快速教程
    3. 提交Issue反馈问题
    """)


def render_indicators_guide():
    """渲染技术指标说明"""
    st.markdown("""
    ## 📊 技术指标说明

    ### MA 均线（Moving Average）

    **原理**：
    - 计算一段时间内的平均价格
    - 常用周期：5日、10日、20日、60日

    **使用方法**：
    - **多头排列**：短期均线在上，长期均线在下 → 看涨信号
    - **空头排列**：短期均线在下，长期均线在上 → 看跌信号
    - **金叉**：短期均线上穿长期均线 → 买入信号
    - **死叉**：短期均线下穿长期均线 → 卖出信号

    **适用场景**：趋势明确的市场

    ---

    ### MACD 指标

    **原理**：
    - DIF（快线）= EMA(12) - EMA(26)
    - DEA（慢线）= EMA(DIF, 9)
    - MACD = (DIF - DEA) × 2

    **使用方法**：
    - **金叉**：DIF上穿DEA，且MACD由负转正 → 强烈买入信号
    - **死叉**：DIF下穿DEA，且MACD由正转负 → 强烈卖出信号
    - **红柱放大**：上涨动能增强
    - **绿柱放大**：下跌动能增强

    **适用场景**：趋势市场，捕捉买卖点

    ---

    ### KDJ 指标

    **原理**：
    - K值：快速随机值
    - D值：慢速随机值
    - J值：乖离值

    **使用方法**：
    - **超买区**：K/D > 80 → 可能回调
    - **超卖区**：K/D < 20 → 可能反弹
    - **金叉**：K线上穿D线 → 买入信号
    - **低位金叉**：在超卖区金叉 → 更可靠
    - **高位死叉**：在超买区死叉 → 更可靠

    **适用场景**：震荡市场，捕捉超买超卖

    ---

    ### RSI 指标（Relative Strength Index）

    **原理**：
    - 衡量价格上涨和下跌的力度
    - 取值范围：0-100

    **使用方法**：
    - **超买**：RSI > 70 → 可能回调
    - **超卖**：RSI < 30 → 可能反弹
    - **强势**：RSI > 50
    - **弱势**：RSI < 50
    - **背离**：价格创新高但RSI不创新高 → 顶部信号

    **适用场景**：震荡市场，判断超买超卖

    ---

    ### BOLL 布林带（Bollinger Bands）

    **原理**：
    - 上轨 = 中轨 + 2×标准差
    - 中轨 = 20日均线
    - 下轨 = 中轨 - 2×标准差

    **使用方法**：
    - **触及上轨**：可能回调或突破
    - **触及下轨**：可能反弹或破位
    - **收口**：波动减小，即将变盘
    - **开口**：波动增大，趋势形成
    - **价格在中轨上方**：强势
    - **价格在中轨下方**：弱势

    **适用场景**：判断波动范围和突破时机

    ---

    ### ATR 真实波幅（Average True Range）

    **原理**：
    - 衡量价格波动的剧烈程度
    - 不考虑方向，只看波动幅度

    **使用方法**：
    - **ATR上升**：波动增大，注意风险
    - **ATR下降**：波动减小，可能整理
    - **设置止损**：ATR的2-3倍作为止损位

    **适用场景**：风险管理和止损设置
    """)


def render_strategy_guide():
    """渲染策略原理"""
    st.markdown("""
    ## ⚙️ 策略原理详解

    ### 趋势型策略

    #### 均线多头排列
    **原理**：
    - 短期均线 > 中期均线 > 长期均线
    - 表示上升趋势明确

    **最佳使用场景**：
    - 牛市或明确上升趋势
    - 成交量配合放大

    **注意事项**：
    - 需确认趋势成立
    - 注意均线发散程度

    ---

    #### MACD金叉
    **原理**：
    - DIF上穿DEA
    - MACD柱由负转正

    **最佳使用场景**：
    - 趋势转折点
    - 下跌后的反弹

    **注意事项**：
    - 零轴上方的金叉更可靠
    - 需配合成交量

    ---

    ### 突破型策略

    #### 箱体突破
    **原理**：
    - 价格突破横盘整理区间
    - 放量确认更可靠

    **最佳使用场景**：
    - 长期横盘后
    - 放量突破

    **注意事项**：
    - 需确认突破有效性
    - 设置止损位

    ---

    #### 放量突破
    **原理**：
    - 价格突破 + 成交量放大
    - 表明资金积极参与

    **最佳使用场景**：
    - 关键阻力位突破
    - 底部启动

    **注意事项**：
    - 突破后需回踩确认
    - 避免假突破

    ---

    ### 震荡型策略

    #### KDJ低位金叉
    **原理**：
    - KDJ在超卖区金叉
    - 表示短期超卖反弹

    **最佳使用场景**：
    - 下跌末期
    - 短线操作

    **注意事项**：
    - 快进快出
    - 严格止损

    ---

    #### RSI超卖
    **原理**：
    - RSI低于30
    - 表示严重超卖

    **最佳使用场景**：
    - 恐慌性下跌
    - 技术性反弹

    **注意事项**：
    - 趋势下跌时慎用
    - 注意风险控制

    ---

    ### 策略组合建议

    **保守型组合**：
    - 均线多头排列（主策略）
    - MACD金叉（确认）
    - 成交量放大（验证）

    **激进型组合**：
    - KDJ低位金叉（信号）
    - RSI超卖（确认）
    - 箱体突破（验证）

    **趋势跟踪组合**：
    - 均线多头排列（趋势）
    - MACD红柱放大（动能）
    - 价格站稳中轨（位置）
    """)


def render_troubleshooting():
    """渲染故障排查"""
    st.markdown("""
    ## 🔧 故障排查

    ### 应用启动问题

    **问题：启动失败，提示端口被占用**
    ```
    解决方法：
    1. 检查是否有其他Streamlit应用在运行
    2. 关闭占用8501端口的程序
    3. 或使用以下命令指定其他端口：
       streamlit run app.py --server.port 8502
    ```

    **问题：启动后页面空白**
    ```
    解决方法：
    1. 检查浏览器控制台是否有错误
    2. 清除浏览器缓存
    3. 尝试使用其他浏览器
    4. 重新启动应用
    ```

    ### 数据下载问题

    **问题：下载失败，提示网络错误**
    ```
    解决方法：
    1. 检查网络连接
    2. 确认能访问baostock服务器
    3. 减少同时下载的股票数量
    4. 增加下载延迟时间
    ```

    **问题：下载的数据为空**
    ```
    解决方法：
    1. 检查股票代码格式是否正确
    2. 确认股票是否存在
    3. 检查日期范围是否合理
    4. 某些新股可能历史数据不足
    ```

    **问题：下载速度很慢**
    ```
    解决方法：
    1. 避开交易时段（9:30-15:00）
    2. 减少同时下载的股票数量
    3. 缩短日期范围
    4. 分批下载不同股票
    ```

    ### 数据显示问题

    **问题：图表不显示**
    ```
    解决方法：
    1. 检查是否有数据
    2. 确认指标已计算
    3. 刷新页面
    4. 检查浏览器兼容性
    ```

    **问题：指标数据为空**
    ```
    解决方法：
    1. 先在"技术指标"页面计算指标
    2. 确认有足够的K线数据
    3. 检查计算参数是否合理
    ```

    ### 选股执行问题

    **问题：选股结果为空**
    ```
    可能原因：
    1. 策略条件过于严格
    2. 数据未更新或缺失
    3. 股票池为空
    4. 市场环境不适用

    解决方法：
    1. 放宽策略参数
    2. 更新数据
    3. 检查股票池
    4. 更换策略类型
    ```

    **问题：选股速度很慢**
    ```
    解决方法：
    1. 减少股票池数量
    2. 优化策略条件
    3. 使用索引（已自动创建）
    4. 清理历史数据
    ```

    ### 性能问题

    **问题：应用运行卡顿**
    ```
    解决方法：
    1. 关闭不需要的浏览器标签
    2. 清除浏览器缓存
    3. 减少数据展示量
    4. 增加系统内存
    5. 使用数据分页功能
    ```

    **问题：内存占用过高**
    ```
    解决方法：
    1. 缩短数据查询范围
    2. 定期清理历史记录
    3. 减少同时打开的图表
    4. 重启应用
    ```

    ### 数据库问题

    **问题：数据库锁定**
    ```
    解决方法：
    1. 关闭所有应用实例
    2. 检查是否有其他程序占用数据库
    3. 重启应用
    4. 如数据库损坏，删除后重新初始化
    ```

    **问题：数据丢失**
    ```
    解决方法：
    1. 检查data/stock_data.db文件是否存在
    2. 恢复备份的数据库文件
    3. 如无备份，重新下载和计算数据
    ```

    ### 获取帮助

    如果以上方法无法解决问题：

    1. **查看日志**：
       - 位置：`logs/app.log`
       - 记录详细的错误信息

    2. **提交Issue**：
       - 描述问题详细情况
       - 提供错误日志
       - 说明系统环境

    3. **查看文档**：
       - 完整使用文档
       - 快速教程
       - 常见问题FAQ
    """)


# ============ 主应用 ============

def main():
    """主应用函数"""

    # 初始化会话状态
    init_session_state()

    # 侧边栏导航
    with st.sidebar:
        st.markdown(f"### {config.APP_NAME}")
        st.markdown(f"**v{config.APP_VERSION}**")
        st.markdown("---")

        page = st.radio(
            "导航菜单",
            [
                "🏠 首页",
                "📊 数据管理",
                "📈 技术指标",
                "⚙️ 策略配置",
                "🎛️ 选股器",
                "🎯 执行选股",
                "🔔 实时监控",
                "📚 帮助文档"
            ],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # 快速链接
        st.markdown("### 🚀 快速开始")
        if st.button("📖 快速教程", use_container_width=True):
            st.session_state.show_tutorial = True
            st.rerun()

        st.markdown("---")
        st.caption(f"{config.APP_DESCRIPTION}")

    # 显示教程（如果激活）
    if st.session_state.get('show_tutorial', False):
        from utils.onboarding import render_quick_tutorial
        render_quick_tutorial()
        return

    # 首次运行引导
    from utils.onboarding import check_first_run, render_welcome_modal
    if check_first_run():
        render_welcome_modal()

    # 路由到不同页面
    if page == "🏠 首页":
        render_home()
    elif page == "📊 数据管理":
        render_data_manager()
        from utils.onboarding import render_context_help
        render_context_help(page)
    elif page == "📈 技术指标":
        render_indicators()
        from utils.onboarding import render_context_help
        render_context_help(page)
    elif page == "⚙️ 策略配置":
        render_strategies()
        from utils.onboarding import render_context_help
        render_context_help(page)
    elif page == "🎛️ 选股器":
        render_screener()
        from utils.onboarding import render_context_help
        render_context_help(page)
    elif page == "🎯 执行选股":
        render_selector()
        from utils.onboarding import render_context_help
        render_context_help(page)
    elif page == "🔔 实时监控":
        render_monitor()
        from utils.onboarding import render_context_help
        render_context_help(page)
    elif page == "📚 帮助文档":
        render_help()


if __name__ == "__main__":
    main()
