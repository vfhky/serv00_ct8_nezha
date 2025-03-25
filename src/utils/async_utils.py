#!/usr/bin/env python3
import asyncio
import concurrent.futures
from typing import List, Callable, Any, Dict, TypeVar, Optional, Union
from functools import partial
import time
import contextlib

from ..utils.logger_wrapper import LoggerWrapper

logger = LoggerWrapper()
T = TypeVar('T')

# 全局线程池
_thread_pool = concurrent.futures.ThreadPoolExecutor()

def shutdown_thread_pool():
    global _thread_pool
    if _thread_pool:
        logger.info("正在关闭线程池...")
        _thread_pool.shutdown(wait=True)
        logger.info("线程池已关闭")

class AsyncExecutor:
    """通用异步执行器，用于并行处理多个相似的任务"""

    @staticmethod
    async def run_in_thread(func, *args, **kwargs):
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _thread_pool,
            partial(func, *args, **kwargs)
        )

    @staticmethod
    async def run_in_thread_with_timeout(func, timeout: float, *args, **kwargs):
        """在线程池中运行同步函数，带超时控制"""
        try:
            task = AsyncExecutor.run_in_thread(func, *args, **kwargs)
            return await asyncio.wait_for(task, timeout)
        except asyncio.TimeoutError:
            logger.error(f"函数 {func.__name__} 执行超时（{timeout}秒）")
            raise
        except asyncio.CancelledError:
            logger.warning(f"函数 {func.__name__} 被取消")
            raise
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行异常: {str(e)}")
            raise

    @staticmethod
    async def gather_with_concurrency(n: int, *tasks, ignore_exceptions: bool = False):
        """
        控制并发度的异步任务执行器
        
        Args:
            n: 最大并发数
            *tasks: 要执行的任务
            ignore_exceptions: 是否忽略单个任务的异常，继续执行其他任务
        """
        semaphore = asyncio.Semaphore(n)
        results = []
        pending_tasks = set()

        async def _sem_task(task_id, task):
            nonlocal pending_tasks
            try:
                async with semaphore:
                    # 记录任务开始时间
                    start_time = time.time()
                    
                    # 创建任务并添加到待处理集合
                    current_task = asyncio.create_task(task)
                    pending_tasks.add(current_task)
                    
                    try:
                        # 等待任务完成
                        result = await current_task
                        # 计算并记录执行时间
                        elapsed = time.time() - start_time
                        if elapsed > 5.0:  # 记录执行时间超过5秒的任务
                            logger.info(f"Task {task_id} 完成, 耗时: {elapsed:.2f}秒")
                        return result
                    finally:
                        # 无论任务是否成功完成，都从待处理集合中移除
                        pending_tasks.discard(current_task)
            except Exception as e:
                logger.error(f"Task {task_id} 异常: {str(e)}")
                if ignore_exceptions:
                    return None
                raise

        # 创建带有ID的任务列表
        task_list = [_sem_task(i, task) for i, task in enumerate(tasks)]
        
        # 使用异常处理，防止一个任务失败导致所有任务失败
        try:
            if ignore_exceptions:
                results = await asyncio.gather(*task_list, return_exceptions=True)
                # 过滤出成功的结果
                return [r for r in results if not isinstance(r, Exception) and r is not None]
            else:
                return await asyncio.gather(*task_list)
        except asyncio.CancelledError:
            # 如果gather被取消，确保取消所有挂起的任务
            for task in pending_tasks:
                if not task.done():
                    task.cancel()
            # 等待所有任务完成取消操作
            await asyncio.gather(*pending_tasks, return_exceptions=True)
            raise
        finally:
            # 确保所有任务都被适当清理
            for task in task_list:
                if not task.done() and not task.cancelled():
                    task.cancel()

    @staticmethod
    @contextlib.asynccontextmanager
    async def timeout_context(timeout_seconds):
        """
        创建一个超时上下文管理器，可以在代码块内使用
        
        示例:
            async with AsyncExecutor.timeout_context(5):
                # 这段代码必须在5秒内完成，否则会引发TimeoutError
                await some_async_operation()
        """
        try:
            # 创建一个可取消的任务
            task = asyncio.current_task()
            # 设置超时
            timer_handle = asyncio.get_event_loop().call_later(
                timeout_seconds, task.cancel
            )
            yield
        except asyncio.CancelledError:
            # 检查是否由超时引起的取消
            if timer_handle.when() <= asyncio.get_event_loop().time():
                logger.error(f"操作超时（{timeout_seconds}秒）")
                raise asyncio.TimeoutError(f"操作超时（{timeout_seconds}秒）")
            raise
        finally:
            # 清理定时器
            timer_handle.cancel()

    @staticmethod
    async def execute_parallel(items: List[Any],
                               func: Callable,
                               max_concurrency: int = 5,
                               timeout: Optional[float] = None,
                               ignore_exceptions: bool = False,
                               **kwargs) -> List[Optional[T]]:
        """
        并行执行指定函数，处理列表中的每个项目

        Args:
            items: 要处理的项目列表
            func: 处理单个项目的函数
            max_concurrency: 最大并发数
            timeout: 每个任务的超时时间（秒），None表示无超时
            ignore_exceptions: 是否忽略单个任务的异常，继续执行其他任务
            **kwargs: 传递给func的额外参数

        Returns:
            处理结果列表
        """
        if not items:
            return []
            
        tasks = []
        for item in items:
            if timeout is not None:
                task = AsyncExecutor.run_in_thread_with_timeout(func, timeout, item, **kwargs)
            else:
                task = AsyncExecutor.run_in_thread(func, item, **kwargs)
            tasks.append(task)

        return await AsyncExecutor.gather_with_concurrency(
            max_concurrency, 
            *tasks, 
            ignore_exceptions=ignore_exceptions
        )
