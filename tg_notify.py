#!/usr/bin/env python3
from datetime import datetime
import pytz
import asyncio
from telegram import Bot
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry

class TgNotify:
    _instance = None

    def __new__(cls, sys_config_entry: SysConfigEntry):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, sys_config_entry: SysConfigEntry):
        if self._initialized:
            return
        self._initialized = True
        self.sys_config_entry = sys_config_entry
        self.logger = LoggerWrapper()
        self.bot = Bot(token=self.sys_config_entry.get("TG_ROBOT_KEY"))
        self.chat_id = self.sys_config_entry.get("TG_CHAT_ID")

    async def send_notify_async(self, title: str, content: str) -> None:
        message = self._build_message(title, content)
        try:
            response = await self.bot.send_message(chat_id=self.chat_id, text=message)
            self.logger.info(f"Telegram推送消息成功，响应内容: {response}")
        except Exception as e:
            self.logger.error(f"Telegram推送消息失败，错误信息: {e}")

    def check_monitor_url_dns_fail_notify(self, url: str, e: Exception):
        title = "💣 解析失败提醒 💣"
        content = f"域名: {url}\n错误: {e}\n请检查dns解析"
        self.logger.error(f"{title}\n{content}")
        self.send_notify(title, content)

    def check_monitor_url_visit_ok_notify(self, url: str, response):
        title = "🎉 当前服务稳如泰山 🎉"
        content = f"域名: {url}\n状态码: {response.status_code}\n继续加油！"
        self.logger.info(f"监控域名{url} {title}\n{content}")
        self.send_notify(title, content)

    def check_monitor_url_visit_fail_notify(self, url: str, response):
        title = "💥 当前服务不可用 💥"
        content = f"域名: {url}\n状态码: {response.status_code}\n心跳模块会拉起进程，请稍后检查"
        self.logger.info(f"监控域名{url} {title}\n{content}")
        self.send_notify(title, content)

    def _build_message(self, title: str, content: str) -> str:
        system_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        return f"----- {title} -----\n{content}\n系统时间: {system_time}\n北京时间: {beijing_time}"

    def send_notify(self, title: str, content: str):
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.send_notify_async(title, content))
        except RuntimeError:
            asyncio.run(self.send_notify_async(title, content))
