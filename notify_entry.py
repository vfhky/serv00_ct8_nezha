#!/usr/bin/env python3
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry
from qywx_notify import QywxNotify
from qywx_app_notify import QywxAppNotify
from tg_notify import TgNotify
from pushplus_notify import PushPlusNotify

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
        self.qywx_notify = QywxNotify(self.sys_config_entry) if self.sys_config_entry.get("ENABLE_QYWX_NOTIFY") == "1" else None
        self.qywx_app_notify = QywxAppNotify(self.sys_config_entry) if self.sys_config_entry.get("ENABLE_QYWX_APP_NOTIFY") == "1" else None
        self.tg_notify = TgNotify(self.sys_config_entry) if self.sys_config_entry.get("ENABLE_TG_NOTIFY") == "1" else None
        self.pushplus_notify = PushPlusNotify(self.sys_config_entry) if self.sys_config_entry.get("ENABLE_PUSHPLUS_NOTIFY") == "1" else None

    def check_monitor_url_dns_fail_notify(self, url: str, e: Exception):
        self._send_notify("check_monitor_url_dns_fail_notify", url=url, e=e)

    def check_monitor_url_visit_ok_notify(self, url: str, response):
        self._send_notify("check_monitor_url_visit_ok_notify", url=url, response=response)

    def check_monitor_url_visit_fail_notify(self, url: str, response):
        self._send_notify("check_monitor_url_visit_fail_notify", url=url, response=response)

    def _send_notify(self, method_name: str, **kwargs):
        if self.qywx_notify:
            getattr(self.qywx_notify, method_name)(**kwargs)
        if self.qywx_app_notify:
            getattr(self.qywx_app_notify, method_name)(**kwargs)
        if self.tg_notify:
            getattr(self.tg_notify, method_name)(**kwargs)
        if self.pushplus_notify:
            getattr(self.pushplus_notify, method_name)(**kwargs)
