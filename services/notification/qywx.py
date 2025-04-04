import json
from typing import Optional, Dict, Any
import requests
from services.notification.base import NotifierBase
from services.notification.factory import NotificationFactory
from config.base import ConfigBase
from utils.logger import get_logger
from utils.decorators import singleton

logger = get_logger()

@singleton
class QywxNotifier(NotifierBase):
    """
    企业微信机器人通知实现
    """

    def __init__(self):
        self.enabled = False
        self.robot_key = None

    @classmethod
    def initialize(cls, config: ConfigBase) -> 'QywxNotifier':
        """
        初始化通知实例

        Args:
            config: 配置实例

        Returns:
            QywxNotifier: 通知实例
        """
        instance = cls()
        instance.enabled = config.get('ENABLE_QYWX_NOTIFY') == '1'
        instance.robot_key = config.get('QYWX_ROBOT_KEY')

        if instance.enabled and not instance.robot_key:
            logger.warning("企业微信机器人通知已启用，但未配置机器人密钥")
            instance.enabled = False

        # 注册到工厂
        NotificationFactory.register_notifier('qywx', instance)

        return instance

    def is_enabled(self) -> bool:
        """
        检查通知服务是否启用

        Returns:
            bool: 服务是否启用
        """
        return self.enabled and self.robot_key is not None

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
            logger.warning("企业微信机器人通知未启用")
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
            "msgtype": "text",
            "text": {
                "content": content
            }
        }

        # 发送请求
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.robot_key}"
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
                    logger.info(f"企业微信机器人通知发送成功")
                    return True
                else:
                    logger.error(f"企业微信机器人通知发送失败: {result.get('errmsg')}")
            else:
                logger.error(f"企业微信机器人通知发送失败，状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"企业微信机器人通知发送异常: {str(e)}")

        return False

# 创建实例并注册
qywx_notifier = QywxNotifier()
