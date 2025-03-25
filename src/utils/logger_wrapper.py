import os
import logging
from logging.handlers import RotatingFileHandler
import pytz
from datetime import datetime
import sys

beijing_tz = pytz.timezone('Asia/Shanghai')

class LoggerWrapper:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggerWrapper, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_file_name='main.log', max_bytes=5 * 1024 * 1024, backup_count=3):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 获取项目根目录（更可靠的方法）
        try:
            # 使用__file__获取当前文件的路径
            current_file_path = os.path.abspath(__file__)
            # 获取src/utils目录
            utils_dir = os.path.dirname(current_file_path)
            # 获取src目录
            src_dir = os.path.dirname(utils_dir)
            # 获取项目根目录
            root_dir = os.path.dirname(src_dir)
            
            # 创建logs目录在项目根目录下
            log_dir = os.path.join(root_dir, 'logs')
        except Exception as e:
            # 如果发生异常，回退到当前目录
            print(f"Error determining project root directory: {str(e)}")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(script_dir, 'logs')
        
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, log_file_name)

        self.logger = logging.getLogger('serv00_ct8_nezha_logger')
        self.logger.setLevel(logging.INFO)
        
        # 添加控制台日志处理器
        if not self.logger.handlers:
            # 文件处理器
            file_handler = RotatingFileHandler(
                log_file_path, 
                maxBytes=max_bytes, 
                backupCount=backup_count, 
                encoding='utf-8'
            )
            # 添加更详细的日志格式，包括日志级别
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # 控制台处理器（可选）
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.WARNING)  # 只在控制台显示警告及以上级别
            self.logger.addHandler(console_handler)

        self._initialized = True

    def _log(self, level, message):
        try:
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            current_weekday_name = weekdays[datetime.now(beijing_tz).weekday()]
            beijing_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"{beijing_time} - {current_weekday_name} - {message}"
            
            log_method = getattr(self.logger, level)
            log_method(log_entry)
        except Exception as e:
            # 如果日志记录失败，尝试打印到控制台
            print(f"日志记录失败: {str(e)}, 原始消息: {message}")

    def info(self, message):
        self._log('info', message)

    def error(self, message):
        self._log('error', message)

    def warning(self, message):
        self._log('warning', message)

    def debug(self, message):
        self._log('debug', message)

    def critical(self, message):
        self._log('critical', message)

    def exception(self, message):
        """记录异常信息，包括堆栈跟踪"""
        self.logger.exception(message)
