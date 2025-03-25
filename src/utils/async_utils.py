#!/usr/bin/env python3
import asyncio
import concurrent.futures
from typing import List, Callable, Any, Dict, TypeVar, Optional
from functools import partial

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
    async def gather_with_concurrency(n: int, *tasks):
        """控制并发度的异步任务执行器"""
        semaphore = asyncio.Semaphore(n)

        async def _sem_task(task):
            async with semaphore:
                return await task

        return await asyncio.gather(*(
            _sem_task(task) for task in tasks
        ))

    @staticmethod
    async def execute_parallel(items: List[Any],
                               func: Callable,
                               max_concurrency: int = 5,
                               **kwargs) -> List[Optional[T]]:
        """
        并行执行指定函数，处理列表中的每个项目

        Args:
            items: 要处理的项目列表
            func: 处理单个项目的函数
            max_concurrency: 最大并发数
            **kwargs: 传递给func的额外参数

        Returns:
            处理结果列表
        """
        tasks = []
        for item in items:
            task = AsyncExecutor.run_in_thread(func, item, **kwargs)
            tasks.append(task)

        return await AsyncExecutor.gather_with_concurrency(max_concurrency, *tasks)
