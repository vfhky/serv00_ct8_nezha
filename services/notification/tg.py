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
class TelegramNotifier(NotifierBase):
    """
    Telegram通知实现
    """

    def __init__(self):
        self.enabled = False
        self.robot_key = None
        self.chat_id = None

    @classmethod
    def initialize(cls, config: ConfigBase) -> 'TelegramNotifier':
        """
        初始化通知实例

        Args:
            config: 配置实例

        Returns:
            TelegramNotifier: 通知实例
        """
        instance = cls()
        instance.enabled = config.get('ENABLE_TG_NOTIFY') == '1'
        instance.robot_key = config.get('TG_ROBOT_KEY')
        instance.chat_id = config.get('TG_CHAT_ID')

        if instance.enabled and (not instance.robot_key or not instance.chat_id):
            logger.warning("Telegram通知已启用，但未配置机器人密钥或聊天ID")
            instance.enabled = False

        # 注册到工厂
        NotificationFactory.register_notifier('telegram', instance)

        return instance

    def is_enabled(self) -> bool:
        """
        检查通知服务是否启用

        Returns:
            bool: 服务是否启用
        """
        return self.enabled and self.robot_key is not None and self.chat_id is not None

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
            logger.warning("Telegram通知未启用")
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

        # 发送请求
        url = f"https://api.telegram.org/bot{self.robot_key}/sendMessage"
        try:
            response = requests.post(
                url=url,
                data={
                    "chat_id": self.chat_id,
                    "text": content,
                    "parse_mode": "Markdown"
                },
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"Telegram通知发送成功")
                    return True
                else:
                    logger.error(f"Telegram通知发送失败: {result.get('description')}")
            else:
                logger.error(f"Telegram通知发送失败，状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"Telegram通知发送异常: {str(e)}")

        return False

# 创建实例并注册
tg_notifier = TelegramNotifier()
