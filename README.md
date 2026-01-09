# 股票量化选股系统

> 新手友好的股票量化选股工具 - 无需编程，一键启动

## 📋 项目简介

这是一个专为股市新手设计的量化选股系统，用户无需编程知识，通过简单的Web界面即可：

- 📊 自动下载股票数据（支持多周期）
- 📈 计算常用技术指标
- ⚙️ 可视化配置选股策略
- 🎯 一键执行选股
- 🔔 实时监控股票变化

## 🎯 主要特性

- **零编程门槛**：纯Web界面，可视化操作
- **一键启动**：自动安装依赖，自动初始化数据库
- **多周期支持**：日线、60分钟、30分钟、15分钟、5分钟
- **16种策略模板**：趋势型、突破型、震荡型策略
- **技术指标完善**：MA、MACD、KDJ、RSI、BOLL、ATR等
- **实时监控**：价格和技术指标监控，自动提醒
- **数据可视化**：K线图、指标图、结果图表

## 🚀 快速开始

### Windows用户

#### anaconda下载地址
下载地址：
https://mirrors.tuna.tsinghua.edu.cn/anaconda/archive/

#### python下载地址，建议用3.12.10
https://www.python.org/downloads/windows/

双击运行 `start.bat`，或在命令行执行：

```batch
cd stock_web_app
start.bat
```

### macOS/Linux用户

在终端执行：

```bash
cd stock_web_app
chmod +x start.sh
./start.sh
```

### 首次运行

首次运行会自动：
1. 创建Python虚拟环境
2. 安装所有依赖包
3. 初始化SQLite数据库
4. 启动Web应用

启动成功后，访问：**http://localhost:8501**

## 📁 项目结构

```
stock_web_app/
├── app.py                  # Streamlit主应用
├── config.py               # 配置文件
├── requirements.txt        # 依赖列表
├── start.sh                # Linux/macOS启动脚本
├── start.bat               # Windows启动脚本
├── README.md               # 项目说明
│
├── data/                   # 数据目录
│   ├── stock_data.db      # SQLite数据库
│   ├── cache/             # 缓存目录
│   └── exports/           # 导出文件目录
│
├── modules/                # 功能模块
│   ├── data_manager.py    # 数据管理模块（开发中）
│   ├── indicators.py      # 技术指标模块（开发中）
│   ├── strategies.py      # 策略配置模块（开发中）
│   ├── selector.py        # 选股执行模块（开发中）
│   └── monitor.py         # 实时监控模块（开发中）
│
├── utils/                  # 工具类
│   ├── db_helper.py       # 数据库工具 ✅
│   ├── baostock_client.py # baostock客户端 ✅
│   ├── indicator_calc.py  # 指标计算工具（待开发）
│   └── plot_utils.py      # 绘图工具（待开发）
│
├── templates/              # 模板文件
│   ├── strategy_templates.json # 策略模板（待开发）
│   └── help.md            # 帮助文档（待开发）
│
└── logs/                   # 日志目录
    └── app.log
```

## 💻 系统要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows / macOS / Linux
- **内存**: 最低 4GB，推荐 8GB+
- **磁盘**: 最低 2GB 可用空间

## 📦 依赖包

主要依赖：
- streamlit >= 1.28.0 (Web框架)
- pandas >= 2.0.0 (数据处理)
- baostock >= 0.8.8 (数据源)
- plotly >= 5.17.0 (数据可视化)

完整依赖列表见 [requirements.txt](./requirements.txt)

## 🎓 使用指南

### 1. 下载数据

在"数据管理"页面：
1. 输入股票代码（如：600519.SH）
2. 选择日期范围
3. 点击"开始下载"

### 2. 配置策略

在"策略配置"页面：
1. 选择策略类型（趋势型/突破型/震荡型）
2. 调整策略参数
3. 保存策略

### 3. 执行选股

在"执行选股"页面：
1. 选择已保存的策略
2. 选择股票池
3. 点击"开始选股"

### 4. 查看结果

- 查看选股结果表格
- 按指标值排序
- 导出为Excel

## 🔧 开发进度

- [x] Phase 1: 基础框架搭建
- [ ] Phase 2: 核心功能开发
- [ ] Phase 3: 增强功能开发
- [ ] Phase 4: 优化与上线

详细任务列表见 [tasks.md](../tasks.md)

## 📄 许可证

本项目仅供学习研究使用，不构成投资建议。

## ⚠️ 免责声明

1. 本系统仅供学习研究使用，不构成投资建议
2. 股市有风险，投资需谨慎
3. 历史表现不代表未来收益
4. 使用本系统产生的一切后果由用户自行承担

---

**版本**: v1.0.0
**最后更新**: 2025-01-03
