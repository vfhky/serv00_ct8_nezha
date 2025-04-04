import json
import time
from typing import Optional, Dict, Any
import requests
from services.notification.base import NotifierBase
from services.notification.factory import NotificationFactory
from config.base import ConfigBase
from utils.logger import get_logger
from utils.decorators import singleton

logger = get_logger()

@singleton
class QywxAppNotifier(NotifierBase):
    """
    企业微信应用通知实现
    """
    def __init__(self):
        self.enabled = False
        self.corp_id = None
        self.corp_secret = None
        self.agent_id = None
        self.notify_user = '@all'
        self.access_token = None
        self.token_expires_at = 0

    @classmethod
    def initialize(cls, config: ConfigBase) -> 'QywxAppNotifier':
        """
        初始化通知实例

        Args:
            config: 配置实例

        Returns:
            QywxAppNotifier: 通知实例
        """
        instance = cls()
        instance.enabled = config.get('ENABLE_QYWX_APP_NOTIFY') == '1'
        instance.corp_id = config.get('QYWX_APP_CROP_ID')
        instance.corp_secret = config.get('QYWX_APP_SECRET')
        instance.agent_id = config.get('QYWX_APP_AGENT_ID')

        notify_user = config.get('QYWX_APP_NOTIFY_USER')
        if notify_user:
            instance.notify_user = notify_user

        if instance.enabled and (not instance.corp_id or not instance.corp_secret or not instance.agent_id):
            logger.warning("企业微信应用通知已启用，但未配置企业ID、应用密钥或应用ID")
            instance.enabled = False

        # 注册到工厂
        NotificationFactory.register_notifier('qywx_app', instance)

        return instance

    def is_enabled(self) -> bool:
        """
        检查通知服务是否启用

        Returns:
            bool: 服务是否启用
        """
        return (self.enabled and self.corp_id is not None and
                self.corp_secret is not None and self.agent_id is not None)

    def _get_access_token(self) -> Optional[str]:
        """
        获取访问令牌

        Returns:
            Optional[str]: 访问令牌，如果获取失败则返回None
        """
        current_time = int(time.time())

        # 如果令牌有效，直接返回
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token

        # 获取新令牌
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    self.access_token = result.get('access_token')
                    self.token_expires_at = current_time + result.get('expires_in', 7200) - 300  # 提前5分钟过期
                    return self.access_token
                else:
                    logger.error(f"获取企业微信访问令牌失败: {result.get('errmsg')}")
            else:
                logger.error(f"获取企业微信访问令牌失败，状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"获取企业微信访问令牌异常: {str(e)}")

        return None

    def notify(self, message: str, level: str = 'info', **kwargs) -> bool:
        """
        发送通知

        Args:
            message: 通知内容
            level: 通知级别，如 'info', 'warning', 'error'
            **kwargs: 其他参数

        Returns:
            bool: 通知是否发送成功
        """
        if not self.is_enabled():
            logger.warning("企业微信应用通知未启用")
            return False

        # 获取访问令牌
        access_token = self._get_access_token()
        if not access_token:
            logger.error("获取企业微信访问令牌失败，无法发送通知")
            return False

        # 根据级别设置标题
        if level == 'error':
            title = '🚨 错误通知'
        elif level == 'warning':
            title = '⚠️ 警告通知'
        else:
            title = '📢 信息通知'

        # 添加额外信息
        content = f"{title}\n\n{message}"

        # 构建请求数据
        data = {
            "touser": self.notify_user,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            }
        }

        # 发送请求
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        try:
            response = requests.post(
                url=url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(data),
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info(f"企业微信应用通知发送成功")
                    return True
                else:
                    logger.error(f"企业微信应用通知发送失败: {result.get('errmsg')}")
            else:
                logger.error(f"企业微信应用通知发送失败，状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"企业微信应用通知发送异常: {str(e)}")

        return False

# 创建实例并注册
qywx_app_notifier = QywxAppNotifier()
