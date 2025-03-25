import requests
from datetime import datetime
import pytz
from typing import Dict
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry

class QywxNotify:
    _instance = None
    QYWX_API_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}'

    def __new__(cls, sys_config_entry: SysConfigEntry):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, sys_config_entry: SysConfigEntry):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.sys_config_entry = sys_config_entry
        self.logger = LoggerWrapper()
        self.qywx_robot_key = self.sys_config_entry.get("QYWX_ROBOT_KEY")
        self.qywx_robot_url = self.QYWX_API_URL.format(self.qywx_robot_key)
        self.headers = {'Content-Type': 'application/json'}

    def check_monitor_url_dns_fail_notify(self, url: str, e: Exception):
        title = "[炸弹]解析失败提醒[炸弹]"
        content = f"域名: {url}\n错误: {e}\n请检查dns解析"
        self.logger.error(f"{title}\n{content}")
        self._send_notify(title, content)

    def check_monitor_url_visit_ok_notify(self, url: str, response):
        title = "[鼓掌]当前服务稳如泰山[鼓掌]"
        content = f"域名: {url}\n状态码: {response.status_code}\n继续加油！"
        self.logger.info(f"监控域名{url} {title}\n{content}")
        self._send_notify(title, content)

    def check_monitor_url_visit_fail_notify(self, url: str, response):
        title = "[裂开]当前服务不可用[裂开]"
        content = f"域名: {url}\n状态码: {response.status_code}\n心跳模块会拉起进程，请稍后检查"
        self.logger.info(f"监控域名{url} {title}\n{content}")
        self._send_notify(title, content)

    def _build_message(self, title: str, content: str) -> Dict[str, Dict[str, str]]:
        system_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        return {
            "msgtype": "text",
            "text": {
                "content": f"----- {title} -----\n{content}\n系统时间: {system_time}\n北京时间: {beijing_time}"
            }
        }

    def _send_notify(self, title: str, content: str) -> None:
        message = self._build_message(title, content)
        try:
            with requests.post(self.qywx_robot_url, json=message, headers=self.headers, timeout=2) as response:
                response.raise_for_status()
                self.logger.info(f"企业微信机器人推送消息成功: {response.text}")
        except requests.RequestException as e:
            self.logger.error(f"企业微信机器人推送消息失败，错误: {str(e)}")
