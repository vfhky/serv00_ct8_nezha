import os
import logging
from logging.handlers import RotatingFileHandler
import pytz
from datetime import datetime
from typing import Optional

# 设置北京时区
beijing_tz = pytz.timezone('Asia/Shanghai')

class LoggerWrapper:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggerWrapper, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_file_name: str = 'main.log', max_bytes: int = 1 * 1024 * 1024, backup_count: int = 1):
        if hasattr(self, '_initialized') and self._initialized:
            return

        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(script_dir, 'log')
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, log_file_name)

        self.logger = logging.getLogger('serv00_ct8_nezha_logger')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._initialized = True

    def _log(self, level: str, message: str) -> None:
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        current_weekday_name = weekdays[datetime.now(beijing_tz).weekday()]
        beijing_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{beijing_time} - {current_weekday_name} - {message}"
        
        log_method = getattr(self.logger, level)
        log_method(log_entry)

    def info(self, message: str) -> None:
        self._log('info', message)

    def error(self, message: str) -> None:
        self._log('error', message)

    def warning(self, message: str) -> None:
        self._log('warning', message)

    def debug(self, message: str) -> None:
        self._log('debug', message)

    def critical(self, message: str) -> None:
        self._log('critical', message)

# 单例获取方法
def get_logger() -> LoggerWrapper:
    """
    获取日志记录器实例
    
    Returns:
        LoggerWrapper: 日志记录器实例
    """
    return LoggerWrapper()
