# -*- coding: utf-8 -*-
"""
错误处理工具
提供统一的错误处理和用户友好的错误提示
"""

import streamlit as st
import traceback
import sys
from typing import Callable, Any, Optional
from functools import wraps
import logging
from datetime import datetime


# ============ 日志配置 ============

def setup_logging():
    """配置日志系统"""
    log_dir = "logs"
    import os
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "app.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


logger = setup_logging()


# ============ 错误类型定义 ============

class AppError(Exception):
    """应用基础错误类"""

    def __init__(self, message: str, user_message: str = None, details: str = None):
        """
        参数:
            message: 错误消息（内部使用）
            user_message: 用户友好的错误消息
            details: 详细信息
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.details = details
        self.timestamp = datetime.now()

        # 记录错误日志
        logger.error(f"{self.__class__.__name__}: {message}")
        if details:
            logger.error(f"Details: {details}")


class DatabaseError(AppError):
    """数据库错误"""

    def __init__(self, message: str, details: str = None):
        user_message = "数据库操作失败，请稍后重试"
        super().__init__(message, user_message, details)


class NetworkError(AppError):
    """网络错误"""

    def __init__(self, message: str, details: str = None):
        user_message = "网络连接失败，请检查网络设置"
        super().__init__(message, user_message, details)


class DataError(AppError):
    """数据错误"""

    def __init__(self, message: str, details: str = None):
        user_message = "数据格式错误或数据不完整"
        super().__init__(message, user_message, details)


class ValidationError(AppError):
    """验证错误"""

    def __init__(self, message: str, details: str = None):
        user_message = "输入数据验证失败，请检查输入"
        super().__init__(message, user_message, details)


class ExternalAPIError(AppError):
    """外部API错误"""

    def __init__(self, message: str, details: str = None):
        user_message = "外部服务调用失败，请稍后重试"
        super().__init__(message, user_message, details)


# ============ 错误处理装饰器 ============

def handle_errors(
    error_message: str = "操作失败",
    show_traceback: bool = False,
    raise_error: bool = False,
    default_return: Any = None
):
    """
    错误处理装饰器

    参数:
        error_message: 默认错误消息
        show_traceback: 是否显示详细错误信息
        raise_error: 是否重新抛出错误
        default_return: 发生错误时的默认返回值

    使用示例:
        @handle_errors(error_message="数据加载失败")
        def load_data():
            # 可能出错的操作
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppError as e:
                # 已知的应用错误
                st.error(f"❌ {e.user_message}")
                if show_traceback and e.details:
                    with st.expander("查看详细信息"):
                        st.code(e.details)
                logger.error(f"AppError in {func.__name__}: {e.message}")
                return default_return
            except Exception as e:
                # 未知错误
                st.error(f"❌ {error_message}")
                if show_traceback:
                    with st.expander("查看错误详情"):
                        st.code(traceback.format_exc())
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                logger.error(traceback.format_exc())
                if raise_error:
                    raise
                return default_return
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    error_message: str = "操作失败",
    default_return: Any = None,
    show_error: bool = True,
    **kwargs
) -> Any:
    """
    安全执行函数

    参数:
        func: 要执行的函数
        *args: 位置参数
        error_message: 错误消息
        default_return: 默认返回值
        show_error: 是否显示错误
        **kwargs: 关键字参数

    返回:
        函数执行结果或默认返回值

    使用示例:
        result = safe_execute(
            risky_function,
            arg1, arg2,
            error_message="处理失败",
            default_return=[]
        )
    """
    try:
        return func(*args, **kwargs)
    except AppError as e:
        if show_error:
            st.error(f"❌ {e.user_message}")
        logger.error(f"AppError in safe_execute: {e.message}")
        return default_return
    except Exception as e:
        if show_error:
            st.error(f"❌ {error_message}")
        logger.error(f"Error in safe_execute: {str(e)}")
        return default_return


# ============ 用户友好的错误提示 ============

def show_database_error(error: Exception):
    """显示数据库错误"""
    st.error("❌ 数据库错误")
    st.markdown("""
    **可能的原因:**
    - 数据库文件被锁定
    - 磁盘空间不足
    - 数据库文件损坏

    **解决方法:**
    1. 关闭其他应用实例
    2. 检查磁盘空间
    3. 如数据库损坏，删除后重新初始化
    """)
    logger.error(f"Database error: {str(error)}")


def show_network_error(error: Exception):
    """显示网络错误"""
    st.error("❌ 网络连接失败")
    st.markdown("""
    **可能的原因:**
    - 网络连接中断
    - baostock服务不可用
    - 防火墙阻止连接

    **解决方法:**
    1. 检查网络连接
    2. 稍后重试
    3. 避开网络高峰时段
    """)
    logger.error(f"Network error: {str(error)}")


def show_data_error(error: Exception):
    """显示数据错误"""
    st.error("❌ 数据错误")
    st.markdown("""
    **可能的原因:**
    - 股票代码格式不正确
    - 数据不完整
    - 数据格式错误

    **解决方法:**
    1. 检查股票代码格式（如：600519.SH）
    2. 重新下载数据
    3. 检查数据完整性
    """)
    logger.error(f"Data error: {str(error)}")


def show_validation_error(error: Exception):
    """显示验证错误"""
    st.error("❌ 输入验证失败")
    st.markdown("""
    **请检查:**
    - 股票代码格式是否正确
    - 日期范围是否合理
    - 参数值是否在有效范围内
    """)
    logger.error(f"Validation error: {str(error)}")


def show_external_api_error(error: Exception):
    """显示外部API错误"""
    st.error("❌ 数据服务连接失败")
    st.markdown("""
    **可能的原因:**
    - baostock服务暂时不可用
    - 请求过于频繁
    - 服务维护中

    **解决方法:**
    1. 稍后重试
    2. 减少请求频率
    3. 避开高峰时段（9:30-15:00）
    """)
    logger.error(f"External API error: {str(error)}")


# ============ 错误映射表 ============

ERROR_HANDLERS = {
    DatabaseError: show_database_error,
    NetworkError: show_network_error,
    DataError: show_data_error,
    ValidationError: show_validation_error,
    ExternalAPIError: show_external_api_error,
}


def show_error(error: Exception):
    """
    根据错误类型显示相应的错误信息

    参数:
        error: 错误对象
    """
    error_type = type(error)

    # 查找匹配的错误处理器
    for error_class, handler in ERROR_HANDLERS.items():
        if isinstance(error, error_class):
            handler(error)
            return

    # 默认错误处理
    st.error(f"❌ 发生错误: {str(error)}")
    logger.error(f"Unhandled error: {str(error)}")


# ============ 确认对话框 ============

def confirm_action(
    action_name: str,
    warning_message: str = None,
    danger: bool = False
) -> bool:
    """
    显示操作确认对话框

    参数:
        action_name: 操作名称
        warning_message: 警告消息
        danger: 是否为危险操作

    返回:
        用户是否确认

    使用示例:
        if confirm_action("删除数据", "此操作不可恢复", danger=True):
            # 执行删除
            pass
    """
    if warning_message:
        st.warning(warning_message)

    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"✅ 确认{action_name}", type="primary" if not danger else "secondary"):
            return True

    with col2:
        if st.button("❌ 取消"):
            return False

    return False


# ============ 操作反馈 ============

def show_success(message: str, duration: int = 3):
    """
    显示成功消息

    参数:
        message: 成功消息
        duration: 显示时长（秒）
    """
    st.success(f"✅ {message}")
    logger.info(f"Success: {message}")


def show_warning(message: str):
    """
    显示警告消息

    参数:
        message: 警告消息
    """
    st.warning(f"⚠️ {message}")
    logger.warning(f"Warning: {message}")


def show_info(message: str):
    """
    显示信息消息

    参数:
        message: 信息消息
    """
    st.info(f"ℹ️ {message}")
    logger.info(f"Info: {message}")


# ============ 加载状态 ============

class LoadingState:
    """加载状态管理器"""

    def __init__(self, message: str = "处理中..."):
        """
        初始化加载状态

        参数:
            message: 加载提示消息
        """
        self.message = message
        self.spinner = None

    def __enter__(self):
        self.spinner = st.spinner(self.message)
        self.spinner.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.spinner:
            self.spinner.__exit__(exc_type, exc_val, exc_tb)

        if exc_type is not None:
            # 发生错误，记录日志
            logger.error(f"Error during loading: {exc_val}")
        return False


# ============ 重试机制 ============

def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    错误重试装饰器

    参数:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
        exceptions: 需要重试的异常类型

    使用示例:
        @retry_on_error(max_retries=3, exceptions=(NetworkError,))
        def fetch_data():
            # 可能失败的网络请求
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time

            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries} retries failed for {func.__name__}"
                        )

            # 所有重试都失败，抛出最后一个异常
            raise last_exception

        return wrapper
    return decorator


# ============ 异常捕获上下文管理器 ============

class ExceptionHandler:
    """异常捕获上下文管理器"""

    def __init__(
        self,
        error_message: str = "操作失败",
        show_error: bool = True,
        log_error: bool = True,
        raise_error: bool = False
    ):
        """
        初始化异常处理器

        参数:
            error_message: 错误消息
            show_error: 是否显示错误
            log_error: 是否记录日志
            raise_error: 是否重新抛出错误
        """
        self.error_message = error_message
        self.show_error = show_error
        self.log_error = log_error
        self.raise_error = raise_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 发生异常
            if self.show_error:
                st.error(f"❌ {self.error_message}")

            if self.log_error:
                logger.error(f"{self.error_message}: {exc_val}")
                logger.error(traceback.format_exc())

            # 不重新抛出异常
            return True

        return False


# ============ 导出的便捷函数 ============

__all__ = [
    'setup_logging',
    'logger',
    'AppError',
    'DatabaseError',
    'NetworkError',
    'DataError',
    'ValidationError',
    'ExternalAPIError',
    'handle_errors',
    'safe_execute',
    'show_error',
    'confirm_action',
    'show_success',
    'show_warning',
    'show_info',
    'LoadingState',
    'retry_on_error',
    'ExceptionHandler',
]
