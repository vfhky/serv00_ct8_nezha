import requests
from datetime import datetime
import pytz
from typing import Dict
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry

class PushPlusNotify:
    _instance = None
    PUSHPLUS_API_URL = 'http://www.pushplus.plus/send'

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
        self.api_token = self.sys_config_entry.get("PUSHPLUS_KEY")
        self.headers = {'Content-Type': 'application/json'}

    def check_monitor_url_dns_fail_notify(self, url: str, e: Exception):
        title = "💣解析失败提醒💣"
        content = f"域名: {url}\n错误: {e}\n请检查dns解析"
        self.logger.error(f"{title}\n{content}")
        self._send_notify(title, content)

    def check_monitor_url_visit_ok_notify(self, url: str, response):
        title = "🎉当前服务稳如泰山🎉"
        content = f"域名: {url}\n状态码: {response.status_code}\n继续加油！"
        self.logger.info(f"监控域名{url} {title}\n{content}")
        self._send_notify(title, content)

    def check_monitor_url_visit_fail_notify(self, url: str, response):
        title = "💥当前服务不可用💥"
        content = f"域名: {url}\n状态码: {response.status_code}\n心跳模块会拉起进程，请稍后检查"
        self.logger.info(f"监控域名{url} {title}\n{content}")
        self._send_notify(title, content)

    def _build_message(self, title: str, content: str) -> Dict[str, str]:
        system_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        return {
            "token": self.api_token,
            "title": title,
            "content": f"----- {title} -----\n{content}\n系统时间: {system_time}\n北京时间: {beijing_time}"
        }

    def _send_notify(self, title: str, content: str) -> None:
        message = self._build_message(title, content)
        try:
            with requests.post(self.PUSHPLUS_API_URL, json=message, headers=self.headers, timeout=2) as response:
                response.raise_for_status()
                self.logger.info(f"PushPlus推送消息成功: {response.text}")
        except requests.RequestException as e:
            self.logger.error(f"PushPlus推送消息失败，错误: {str(e)}")
