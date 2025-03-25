#!/usr/bin/env python3
import asyncio
from typing import Any, Dict, Optional, List, Callable

from ..config.sys_config_entry import SysConfigEntry
from ..utils.logger_wrapper import LoggerWrapper
from ..utils.async_utils import AsyncExecutor
from .qywx_notify import QywxNotify
from .qywx_app_notify import QywxAppNotify
from .tg_notify import TgNotify
from .pushplus_notify import PushPlusNotify

class NotifyEntry:
    _instance = None

    def __new__(cls, sys_config_entry: SysConfigEntry):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, sys_config_entry: SysConfigEntry):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.logger = LoggerWrapper()
        self.sys_config_entry = sys_config_entry

        # 初始化通知渠道
        self.notifiers = []

        if self.sys_config_entry.get("ENABLE_QYWX_NOTIFY") == "1":
            self.notifiers.append(QywxNotify(self.sys_config_entry))

        if self.sys_config_entry.get("ENABLE_QYWX_APP_NOTIFY") == "1":
            self.notifiers.append(QywxAppNotify(self.sys_config_entry))

        if self.sys_config_entry.get("ENABLE_TG_NOTIFY") == "1":
            self.notifiers.append(TgNotify(self.sys_config_entry))

        if self.sys_config_entry.get("ENABLE_PUSHPLUS_NOTIFY") == "1":
            self.notifiers.append(PushPlusNotify(self.sys_config_entry))

    def check_monitor_url_dns_fail_notify(self, url: str, e: Exception):
        self._send_notify("check_monitor_url_dns_fail_notify", url=url, e=e)

    def check_monitor_url_visit_ok_notify(self, url: str, response):
        self._send_notify("check_monitor_url_visit_ok_notify", url=url, response=response)

    def check_monitor_url_visit_fail_notify(self, url: str, response):
        self._send_notify("check_monitor_url_visit_fail_notify", url=url, response=response)

    def _send_notify(self, method_name: str, **kwargs):
        """同步发送通知到所有渠道"""
        for notifier in self.notifiers:
            try:
                getattr(notifier, method_name)(**kwargs)
            except Exception as e:
                self.logger.error(f"通知渠道 {notifier.__class__.__name__} 发送失败: {str(e)}")

    async def _send_notify_async(self, method_name: str, **kwargs):
        """异步并行发送通知到所有渠道"""
        if not self.notifiers:
            return

        async def _notify_task(notifier):
            try:
                method = getattr(notifier, method_name)
                await AsyncExecutor.run_in_thread(method, **kwargs)
                return True
            except Exception as e:
                self.logger.error(f"通知渠道 {notifier.__class__.__name__} 发送失败: {str(e)}")
                return False

        tasks = [_notify_task(notifier) for notifier in self.notifiers]
        await asyncio.gather(*tasks)