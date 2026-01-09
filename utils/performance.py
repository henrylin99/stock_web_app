# -*- coding: utf-8 -*-
"""
性能优化工具
提供缓存、性能监控等优化功能
"""

import streamlit as st
import time
import functools
from typing import Callable, Any
import pandas as pd


# ============ 缓存装饰器 ============

def cached_with_ttl(ttl: int = 300, show_hits: bool = False):
    """
    带TTL的缓存装饰器

    参数:
        ttl: 缓存时间（秒），默认5分钟
        show_hits: 是否显示缓存命中信息

    使用示例:
        @cached_with_ttl(ttl=600)
        def expensive_function():
            # 耗时操作
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 使用streamlit的缓存装饰器
            return st.cache_data(ttl=ttl, show_spinner="加载中...")(func)(*args, **kwargs)
        return wrapper
    return decorator


def cached_query(ttl: int = 300):
    """
    数据库查询专用缓存装饰器

    参数:
        ttl: 缓存时间（秒），默认5分钟
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        @st.cache_data(ttl=ttl, show_spinner=False)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============ 性能监控 ============

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics = {}

    def start_timer(self, name: str):
        """开始计时"""
        self.metrics[name] = {'start': time.time()}

    def end_timer(self, name: str) -> float:
        """结束计时并返回耗时"""
        if name in self.metrics:
            elapsed = time.time() - self.metrics[name]['start']
            self.metrics[name]['elapsed'] = elapsed
            return elapsed
        return 0.0

    def get_metric(self, name: str) -> float:
        """获取指标"""
        if name in self.metrics and 'elapsed' in self.metrics[name]:
            return self.metrics[name]['elapsed']
        return 0.0

    def get_all_metrics(self) -> dict:
        """获取所有指标"""
        return {
            name: metric.get('elapsed', 0.0)
            for name, metric in self.metrics.items()
            if 'elapsed' in metric
        }


# 全局性能监控器实例
perf_monitor = PerformanceMonitor()


def track_performance(name: str):
    """
    性能跟踪装饰器

    参数:
        name: 操作名称

    使用示例:
        @track_performance("数据加载")
        def load_data():
            # 加载数据
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            perf_monitor.start_timer(name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                perf_monitor.end_timer(name)
        return wrapper
    return decorator


# ============ 数据分页工具 ============

class DataPaginator:
    """数据分页器"""

    def __init__(self, data: pd.DataFrame, page_size: int = 50):
        """
        初始化分页器

        参数:
            data: 要分页的数据
            page_size: 每页记录数
        """
        self.data = data
        self.page_size = page_size
        self.total_pages = (len(data) + page_size - 1) // page_size if len(data) > 0 else 0

    def get_page(self, page_num: int) -> pd.DataFrame:
        """
        获取指定页的数据

        参数:
            page_num: 页码（从1开始）

        返回:
            该页的数据
        """
        if page_num < 1 or page_num > self.total_pages:
            return pd.DataFrame()

        start_idx = (page_num - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.data.iloc[start_idx:end_idx].copy()

    def get_page_info(self, page_num: int) -> dict:
        """
        获取页码信息

        参数:
            page_num: 当前页码

        返回:
            页码信息字典
        """
        return {
            'current_page': page_num,
            'total_pages': self.total_pages,
            'total_records': len(self.data),
            'page_size': self.page_size,
            'has_prev': page_num > 1,
            'has_next': page_num < self.total_pages
        }

    def render_pagination(self, page_num: int, key: str = 'pagination') -> int:
        """
        渲染分页控件

        参数:
            page_num: 当前页码
            key: 控件键名

        返回:
            用户选择的页码
        """
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("◀️ 上一页", disabled=page_num <= 1, key=f"{key}_prev"):
                page_num = max(1, page_num - 1)
                st.rerun()

        with col2:
            if st.button("下一页 ▶️", disabled=page_num >= self.total_pages, key=f"{key}_next"):
                page_num = min(self.total_pages, page_num + 1)
                st.rerun()

        with col3:
            new_page = st.selectbox(
                "跳转到",
                options=range(1, self.total_pages + 1),
                index=page_num - 1,
                format_func=lambda x: f"第 {x} 页",
                key=f"{key}_select",
                label_visibility="collapsed"
            )
            if new_page != page_num:
                st.rerun()
            page_num = new_page

        with col4:
            st.write(f"共 {self.total_pages} 页")

        with col5:
            st.write(f"{len(self.data)} 条记录")

        return page_num


# ============ 数据加载状态 ============

def with_loading_status(message: str = "加载中..."):
    """
    显示加载状态的装饰器

    参数:
        message: 加载提示消息

    使用示例:
        @with_loading_status("正在下载数据...")
        def download_data():
            # 下载数据
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with st.spinner(message):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ============ 数据分块处理 ============

def process_in_chunks(data: pd.DataFrame, chunk_size: int, process_func: Callable) -> pd.DataFrame:
    """
    分块处理数据

    参数:
        data: 要处理的数据
        chunk_size: 每块大小
        process_func: 处理函数

    返回:
        处理后的数据

    使用示例:
        def process_chunk(chunk):
            # 处理数据块
            return chunk

        result = process_in_chunks(df, 1000, process_chunk)
    """
    results = []

    total_chunks = (len(data) + chunk_size - 1) // chunk_size
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(0, len(data), chunk_size):
        chunk = data.iloc[i:i + chunk_size]
        processed = process_func(chunk)
        results.append(processed)

        # 更新进度
        current_chunk = i // chunk_size + 1
        progress = current_chunk / total_chunks
        progress_bar.progress(progress)
        status_text.text(f"处理中... {current_chunk}/{total_chunks}")

    progress_bar.empty()
    status_text.empty()

    return pd.concat(results, ignore_index=True)


# ============ 内存优化 ============

def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    优化DataFrame内存占用

    参数:
        df: 要优化的DataFrame

    返回:
        优化后的DataFrame
    """
    result = df.copy()

    for col in result.columns:
        col_type = result[col].dtype

        if col_type == 'object':
            # 尝试转换为category类型
            unique_values = result[col].nunique()
            if unique_values / len(result[col]) < 0.5:  # 唯一值少于50%
                result[col] = result[col].astype('category')

        elif col_type == 'float64':
            # 尝试转换为float32
            result[col] = result[col].astype('float32')

        elif col_type == 'int64':
            # 尝试转换为int32或更小的整数类型
            result[col] = pd.to_numeric(result[col], downcast='integer')

    return result


# ============ 懒加载工具 ============

class LazyLoader:
    """懒加载器"""

    def __init__(self, load_func: Callable, *args, **kwargs):
        """
        初始化懒加载器

        参数:
            load_func: 加载函数
            *args, **kwargs: 传递给加载函数的参数
        """
        self.load_func = load_func
        self.args = args
        self.kwargs = kwargs
        self._loaded = False
        self._data = None

    def load(self) -> Any:
        """
        加载数据

        返回:
            加载的数据
        """
        if not self._loaded:
            self._data = self.load_func(*self.args, **self.kwargs)
            self._loaded = True
        return self._data

    def is_loaded(self) -> bool:
        """检查是否已加载"""
        return self._loaded

    def reset(self):
        """重置加载状态"""
        self._loaded = False
        self._data = None


# ============ 性能报告 ============

def render_performance_report():
    """渲染性能报告"""
    metrics = perf_monitor.get_all_metrics()

    if not metrics:
        return

    st.markdown("### 📊 性能报告")

    for name, elapsed in metrics.items():
        # 根据耗时选择颜色
        if elapsed < 0.1:
            color = "🟢"
        elif elapsed < 0.5:
            color = "🟡"
        else:
            color = "🔴"

        st.metric(f"{color} {name}", f"{elapsed:.3f}秒")


# ============ 缓存管理 ============

def clear_cache_button():
    """显示清除缓存按钮"""
    if st.button("🗑️ 清除缓存", key="clear_cache"):
        st.cache_data.clear()
        st.success("✅ 缓存已清除")
        st.rerun()


def show_cache_stats():
    """显示缓存统计信息"""
    # Streamlit不直接提供缓存统计，这里提供占位函数
    st.info("💡 缓存功能已启用，数据将自动缓存以提高性能")


# ============ 数据预加载提示 ============

def show_data_preload_tips():
    """显示数据预加载提示"""
    st.info("""
    💡 **性能提示**:
    - 首次加载数据可能较慢，后续会使用缓存加速
    - 定期清理缓存可以释放内存
    - 大量数据查询建议使用分页功能
    """)
