#!/usr/bin/env python3
import asyncio
import concurrent.futures
from typing import List, Callable, Any, Dict, TypeVar, Optional, Union
from functools import partial
import time

from ..utils.logger_wrapper import LoggerWrapper

logger = LoggerWrapper()
T = TypeVar('T')

class AsyncExecutor:
    """通用异步执行器，用于并行处理多个相似的任务"""

    @staticmethod
    async def run_in_thread(func, *args, **kwargs):
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool,
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

        async def _sem_task(task_id, task):
            try:
                async with semaphore:
                    start_time = time.time()
                    result = await task
                    elapsed = time.time() - start_time
                    if elapsed > 5.0:  # 记录执行时间超过5秒的任务
                        logger.info(f"Task {task_id} 完成, 耗时: {elapsed:.2f}秒")
                    return result
            except Exception as e:
                logger.error(f"Task {task_id} 异常: {str(e)}")
                if ignore_exceptions:
                    return None
                raise

        # 创建带有ID的任务列表
        task_list = [_sem_task(i, task) for i, task in enumerate(tasks)]
        
        # 使用异常处理，防止一个任务失败导致所有任务失败
        if ignore_exceptions:
            results = await asyncio.gather(*task_list, return_exceptions=True)
            # 过滤出成功的结果
            return [r for r in results if not isinstance(r, Exception) and r is not None]
        else:
            return await asyncio.gather(*task_list)

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
