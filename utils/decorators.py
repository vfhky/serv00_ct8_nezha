import functools
import time
from typing import Callable, Any, TypeVar, cast
from utils.logger import get_logger
import threading
from functools import wraps

logger = get_logger()

# 泛型类型
T = TypeVar('T')

def time_count(func: Callable[..., T]) -> Callable[..., T]:
    """
    计时装饰器，用于测量函数执行时间

    Args:
        func: 被装饰的函数

    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time

        if elapsed_time < 60:
            print(f"=======> 函数 {func.__name__} 总共耗时: {elapsed_time:.2f} 秒")
        else:
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            print(f"=======> 函数 {func.__name__} 总共耗时: {int(minutes)} 分 {seconds:.2f} 秒")

        return result
    return cast(Callable[..., T], wrapper)

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """
    重试装饰器，在遇到指定异常时进行重试

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的增长因子
        exceptions: 触发重试的异常类型

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"函数 {func.__name__} 重试失败，达到最大尝试次数 {max_attempts}")
                        raise

                    logger.warning(f"函数 {func.__name__} 尝试 {attempt}/{max_attempts} 失败: {str(e)}，将在 {current_delay:.2f} 秒后重试")
                    time.sleep(current_delay)
                    attempt += 1
                    current_delay *= backoff

            # 这里实际上不会执行到，但为了类型检查添加
            raise RuntimeError("Unreachable code")
        return cast(Callable[..., T], wrapper)
    return decorator

def singleton(cls: Type[T]) -> Type[T]:
    """
    线程安全的单例装饰器

    Args:
        cls: 要装饰的类

    Returns:
        Type[T]: 装饰后的类
    """
    instances = {}
    lock = threading.RLock()

    @wraps(cls)
    def get_instance(*args, **kwargs) -> T:
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
            return instances[cls]

    return get_instance
