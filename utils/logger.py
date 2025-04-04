import os
import logging
import tempfile
from logging.handlers import RotatingFileHandler
import pytz
from datetime import datetime
from utils.decorators import singleton

# 北京时区
beijing_tz = pytz.timezone('Asia/Shanghai')

@singleton
class LoggerWrapper:
    """
    日志包装器，提供统一的日志记录接口
    """
    def __init__(self):
        self.logger = None
        self.initialized = False
        self.log_level = logging.INFO
        self.log_format = '%(asctime)s - %(levelname)s - %(message)s'
        self.date_format = '%Y-%m-%d %H:%M:%S'
        self.log_file = os.path.join(tempfile.gettempdir(), "nezha_manager.log")
        self.max_bytes = 10 * 1024 * 1024  # 10MB
        self.backup_count = 3

    def initialize(self, log_level=None, log_file=None):
        """
        初始化日志记录器

        Args:
            log_level: 日志级别
            log_file: 日志文件路径
        """
        if self.initialized:
            return

        if log_level:
            self.log_level = log_level

        if log_file:
            self.log_file = log_file

        # 创建日志记录器
        self.logger = logging.getLogger('nezha_manager')
        self.logger.setLevel(self.log_level)

        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)

        # 创建文件处理器
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)

        # 创建格式化器
        formatter = logging.Formatter(self.log_format, self.date_format)
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        self.initialized = True

    def _format_message(self, message: str) -> str:
        """
        格式化日志消息，添加时区信息

        Args:
            message: 原始消息

        Returns:
            str: 格式化后的消息
        """
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        current_weekday_name = weekdays[datetime.now(beijing_tz).weekday()]
        return f"{current_weekday_name} - {message}"

    def debug(self, message: str) -> None:
        """
        记录调试级别日志

        Args:
            message: 日志消息
        """
        if not self.initialized:
            self.initialize()
        self.logger.debug(self._format_message(message))

    def info(self, message: str) -> None:
        """
        记录信息级别日志

        Args:
            message: 日志消息
        """
        if not self.initialized:
            self.initialize()
        self.logger.info(self._format_message(message))

    def warning(self, message: str) -> None:
        """
        记录警告级别日志

        Args:
            message: 日志消息
        """
        if not self.initialized:
            self.initialize()
        self.logger.warning(self._format_message(message))

    def error(self, message: str) -> None:
        """
        记录错误级别日志

        Args:
            message: 日志消息
        """
        if not self.initialized:
            self.initialize()
        self.logger.error(self._format_message(message))

    def critical(self, message: str) -> None:
        """
        记录严重错误级别日志

        Args:
            message: 日志消息
        """
        if not self.initialized:
            self.initialize()
        self.logger.critical(self._format_message(message))

# 全局日志记录器实例
logger_wrapper = LoggerWrapper()

def get_logger():
    """
    获取日志记录器实例

    Returns:
        LoggerWrapper: 日志记录器实例
    """
    return logger_wrapper
