import requests
from typing import List, Optional, Dict
from datetime import datetime
import pytz
from ..utils.logger_wrapper import LoggerWrapper
from ..config.sys_config_entry import SysConfigEntry

class QywxAppNotify:
    _instance = None
    QYWX_APP_TOKEN_URL = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
    QYWX_APP_PUSH_URL = 'https://qyapi.weixin.qq.com/cgi-bin/message/send'

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

        self.qywx_app_corp_id = self.sys_config_entry.get("QYWX_APP_CROP_ID")
        self.qywx_app_secret = self.sys_config_entry.get("QYWX_APP_SECRET")
        self.qywx_app_agent_id = self.sys_config_entry.get("QYWX_APP_AGENT_ID")
        self.qywx_app_notify_user = self.sys_config_entry.get("QYWX_APP_NOTIFY_USER", '@all')

        self.qywx_app_token_url = f"{self.QYWX_APP_TOKEN_URL}?corpid={self.qywx_app_corp_id}&corpsecret={self.qywx_app_secret}"
        self.headers = {'Content-Type': 'application/json'}

    def check_monitor_url_dns_fail_notify(self, url: str, e: Exception) -> None:
        title = "[炸弹]解析失败提醒[炸弹]"
        content = f"域名: {url}\n错误: {e}\n请检查dns解析"
        self.logger.error(f"{title}\n{content}")
        self._send_notify(title, content)

    def check_monitor_url_visit_ok_notify(self, url: str, response) -> None:
        title = "[鼓掌]当前服务稳如泰山[鼓掌]"
        content = f"域名: {url}\n状态码: {response.status_code}\n继续加油！"
        self.logger.info(f"监控域名{url} {title}\n{content}")
        self._send_notify(title, content)

    def check_monitor_url_visit_fail_notify(self, url: str, response) -> None:
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
        access_token = self._get_access_token()
        if access_token:
            self._send_message(access_token, message)
        else:
            self.logger.error("获取企业微信访问令牌失败")

    def _get_access_token(self) -> Optional[str]:
        try:
            response = requests.get(self.qywx_app_token_url, timeout=2)
            response.raise_for_status()
            access_token = response.json().get("access_token")
            if not access_token:
                self.logger.error("获取企业微信app应用令牌失败")
            return access_token
        except requests.RequestException as e:
            self.logger.error(f"获取企业微信app应用令牌异常: {e}")
            return None

    def _send_message(self, access_token: str, message: Dict[str, Dict[str, str]]) -> None:
        url = f"{self.QYWX_APP_PUSH_URL}?access_token={access_token}"
        body = {
            "touser": self.qywx_app_notify_user,
            "agentid": self.qywx_app_agent_id,
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0,
            **message
        }

        try:
            with requests.post(url, json=body, headers=self.headers, timeout=2) as response:
                response.raise_for_status()
                self.logger.info(f"企业微信APP推送消息成功: {response.text}")
        except requests.RequestException as e:
            self.logger.error(f"企业微信APP推送消息失败，错误: {str(e)}")
