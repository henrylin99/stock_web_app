# -*- coding: utf-8 -*-
"""
绘图工具
提供股票数据可视化功能
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def create_kline_chart(data, title="K线图", show_volume=True, show_ma=False, show_macd=False, show_kdj=False, show_rsi=False):
    """
    创建K线图表

    参数:
        data: DataFrame，包含OHLCV数据
        title: 图表标题
        show_volume: 是否显示成交量
        show_ma: 是否显示MA均线
        show_macd: 是否显示MACD
        show_kdj: 是否显示KDJ
        show_rsi: 是否显示RSI

    返回:
        plotly Figure对象
    """

    if data is None or len(data) == 0:
        return None

    # 计算子图数量
    subplot_count = 1  # K线图

    if show_macd:
        subplot_count += 1
    if show_kdj:
        subplot_count += 1
    if show_rsi:
        subplot_count += 1
    if show_volume:
        subplot_count += 1

    # 计算行高度
    row_heights = [0.5] + [0.15] * (subplot_count - 1)

    # 创建子图
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
        name='K线',
        increasing_line_color='red',
        decreasing_line_color='green'
    )
    fig.add_trace(candlestick, row=1, col=1)

    # MA均线
    if show_ma:
        ma_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        ma_list = ['ma5', 'ma10', 'ma20', 'ma60']

        for i, ma in enumerate(ma_list):
            if ma in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data['trade_date'],
                        y=data[ma],
                        name=ma.upper(),
                        mode='lines',
                        line=dict(color=ma_colors[i], width=1),
                        hovertemplate='%{y:.2f}'
                    ),
                    row=1, col=1
                )

    # 布林带
    if 'boll_upper' in data.columns and 'boll_lower' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data['trade_date'],
                y=data['boll_upper'],
                name='BOLL上轨',
                mode='lines',
                line=dict(color='rgba(255,0,0,0.3)', width=1),
                hovertemplate='%{y:.2f}',
                fill=None
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=data['trade_date'],
                y=data['boll_lower'],
                name='BOLL下轨',
                mode='lines',
                line=dict(color='rgba(255,0,0,0.3)', width=1),
                hovertemplate='%{y:.2f}',
                fill='tonexty',
                fillcolor='rgba(255,0,0,0.05)'
            ),
            row=1, col=1
        )

    current_row = 2

    # MACD
    if show_macd and 'dif' in data.columns:
        if 'dea' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['dif'],
                    name='DIF',
                    mode='lines',
                    line=dict(color='#FF6B6B', width=1.5),
                    hovertemplate='%{y:.4f}'
                ),
                row=current_row, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['dea'],
                    name='DEA',
                    mode='lines',
                    line=dict(color='#4ECDC4', width=1.5),
                    hovertemplate='%{y:.4f}'
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
                    marker_color=colors,
                    hovertemplate='%{y:.4f}'
                ),
                row=current_row, col=1
            )

        current_row += 1

    # KDJ
    if show_kdj and 'k' in data.columns:
        if 'd' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['k'],
                    name='K',
                    mode='lines',
                    line=dict(color='#FF6B6B', width=1.5),
                    hovertemplate='%{y:.2f}'
                ),
                row=current_row, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['d'],
                    name='D',
                    mode='lines',
                    line=dict(color='#4ECDC4', width=1.5),
                    hovertemplate='%{y:.2f}'
                ),
                row=current_row, col=1
            )

        if 'j' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data['j'],
                    name='J',
                    mode='lines',
                    line=dict(color='#45B7D1', width=1.5),
                    hovertemplate='%{y:.2f}'
                ),
                row=current_row, col=1
            )

        # 添加超买超卖线
        fig.add_hline(y=80, line_dash="dash", line_color="red", row=current_row, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="green", row=current_row, col=1)

        current_row += 1

    # RSI
    if show_rsi and 'rsi6' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data['trade_date'],
                y=data['rsi6'],
                name='RSI6',
                mode='lines',
                line=dict(color='#FF6B6B', width=1.5),
                hovertemplate='%{y:.2f}'
            ),
            row=current_row, col=1
        )

        # 添加超买超卖线
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)

        current_row += 1

    # 成交量
    if show_volume and 'volume' in data.columns:
        colors = ['red' if row['close'] >= row['open'] else 'green'
                  for _, row in data.iterrows()]

        fig.add_trace(
            go.Bar(
                x=data['trade_date'],
                y=data['volume'],
                name='成交量',
                marker_color=colors,
                hovertemplate='%{y:.0f}'
            ),
            row=current_row, col=1
        )

    # 更新布局
    fig.update_layout(
        title=title,
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
        ),
        template='plotly_white'
    )

    return fig


def create_indicator_comparison_chart(data, indicators):
    """
    创建指标对比图表

    参数:
        data: DataFrame，包含OHLCV数据
        indicators: 要对比的指标列表

    返回:
        plotly Figure对象
    """

    if data is None or len(data) == 0:
        return None

    fig = go.Figure()

    for indicator in indicators:
        if indicator in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['trade_date'],
                    y=data[indicator],
                    name=indicator.upper(),
                    mode='lines+markers'
                )
            )

    fig.update_layout(
        title="指标对比",
        xaxis_title="日期",
        yaxis_title="指标值",
        hovermode='x unified',
        template='plotly_white'
    )

    return fig


def create_selection_pie_chart(results, column='industry'):
    """
    创建选股结果饼图

    参数:
        results: 选股结果DataFrame
        column: 分组列

    返回:
        plotly Figure对象
    """

    if results is None or len(results) == 0:
        return None

    # 统计
    value_counts = results[column].value_counts()

    fig = go.Figure(data=[go.Pie(
        labels=value_counts.index,
        values=value_counts.values,
        hole=0.3
    )])

    fig.update_layout(
        title=f"选股结果分布 - {column}",
        template='plotly_white'
    )

    return fig


def create_selection_bar_chart(results, column='strategy', top_n=20):
    """
    创建选股结果柱状图

    参数:
        results: 选股结果DataFrame
        column: 分组列
        top_n: 显示前N个

    返回:
        plotly Figure对象
    """

    if results is None or len(results) == 0:
        return None

    # 统计
    value_counts = results[column].value_counts().head(top_n)

    fig = go.Figure(data=[go.Bar(
        x=value_counts.index,
        y=value_counts.values,
        marker_color='skyblue'
    )])

    fig.update_layout(
        title=f"选股结果统计 - {column} (Top {top_n})",
        xaxis_title=column,
        yaxis_title="数量",
        template='plotly_white'
    )

    return fig
