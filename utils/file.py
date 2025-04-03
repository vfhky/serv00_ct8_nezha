import os
import shutil
from typing import Optional, TextIO, List
from utils.logger import get_logger

logger = get_logger()

def check_file_exists(file_path: str) -> bool:
    """
    检查文件是否存在
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 文件是否存在
    """
    return os.path.exists(file_path)

def ensure_dir_exists(dir_path: str) -> bool:
    """
    确保目录存在，不存在则创建
    
    Args:
        dir_path: 目录路径
        
    Returns:
        bool: 目录是否存在或创建成功
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"已创建目录: {dir_path}")
        except Exception as e:
            logger.error(f"创建目录失败: {dir_path}, 错误: {str(e)}")
            return False
    return True

def write_to_file(content: str, file_path: str) -> bool:
    """
    将内容写入文件
    
    Args:
        content: 要写入的内容
        file_path: 文件路径
        
    Returns:
        bool: 写入是否成功
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not ensure_dir_exists(dir_path):
            return False
        
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        logger.info(f"已写入文件: {file_path}")
        return True
    except Exception as e:
        logger.error(f"写入文件失败: {file_path}, 错误: {str(e)}")
        return False

def append_to_file(content: str, file_path: str) -> bool:
    """
    将内容追加到文件
    
    Args:
        content: 要追加的内容
        file_path: 文件路径
        
    Returns:
        bool: 追加是否成功
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not ensure_dir_exists(dir_path):
            return False
        
        with open(file_path, "a", encoding="utf-8") as file:
            file.write(content)
        logger.info(f"已追加到文件: {file_path}")
        return True
    except Exception as e:
        logger.error(f"追加到文件失败: {file_path}, 错误: {str(e)}")
        return False

def read_file(file_path: str) -> Optional[str]:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[str]: 文件内容，如果读取失败则返回None
    """
    if not check_file_exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        logger.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
        return None

def read_file_lines(file_path: str) -> Optional[List[str]]:
    """
    按行读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[List[str]]: 文件内容的行列表，如果读取失败则返回None
    """
    if not check_file_exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.readlines()
    except Exception as e:
        logger.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
        return None

def copy_file(src_path: str, dst_path: str, create_backup: bool = True) -> bool:
    """
    复制文件
    
    Args:
        src_path: 源文件路径
        dst_path: 目标文件路径
        create_backup: 是否创建备份
        
    Returns:
        bool: 复制是否成功
    """
    if not check_file_exists(src_path):
        logger.error(f"源文件不存在: {src_path}")
        return False
    
    try:
        # 确保目标目录存在
        dst_dir = os.path.dirname(dst_path)
        if dst_dir and not ensure_dir_exists(dst_dir):
            return False
        
        # 如果目标文件存在且需要备份
        if check_file_exists(dst_path) and create_backup:
            backup_path = f"{dst_path}.bak"
            shutil.copy2(dst_path, backup_path)
            logger.info(f"已创建备份: {backup_path}")
        
        # 复制文件
        shutil.copy2(src_path, dst_path)
        logger.info(f"已复制文件: {src_path} -> {dst_path}")
        return True
    except Exception as e:
        logger.error(f"复制文件失败: {src_path} -> {dst_path}, 错误: {str(e)}")
        return False

def get_dashboard_config_file(user_name: str) -> str:
    """
    获取仪表盘配置文件路径
    
    Args:
        user_name: 用户名
        
    Returns:
        str: 仪表盘配置文件路径
    """
    from utils.system import get_dashboard_dir
    config_dir = get_dashboard_dir(user_name)
    return os.path.join(config_dir, 'data/config.yaml')

def get_dashboard_db_file(user_name: str) -> str:
    """
    获取仪表盘数据库文件路径
    
    Args:
        user_name: 用户名
        
    Returns:
        str: 仪表盘数据库文件路径
    """
    from utils.system import get_dashboard_dir
    dashboard_dir = get_dashboard_dir(user_name)
    return os.path.join(dashboard_dir, 'data/sqlite.db')

def get_serv00_config_dir(serv00_ct8_dir: str) -> str:
    """
    获取配置目录路径
    
    Args:
        serv00_ct8_dir: 主目录路径
        
    Returns:
        str: 配置目录路径
    """
    return os.path.join(serv00_ct8_dir, 'config')

def get_serv00_config_file(serv00_ct8_dir: str, file_name: str) -> str:
    """
    获取配置文件路径
    
    Args:
        serv00_ct8_dir: 主目录路径
        file_name: 文件名
        
    Returns:
        str: 配置文件路径
    """
    config_dir = get_serv00_config_dir(serv00_ct8_dir)
    return os.path.join(config_dir, file_name)

def get_serv00_dir_file(serv00_ct8_dir: str, file_name: str) -> str:
    """
    获取主目录下的文件路径
    
    Args:
        serv00_ct8_dir: 主目录路径
        file_name: 文件名
        
    Returns:
        str: 文件路径
    """
    return os.path.join(serv00_ct8_dir, file_name)
