import os
from typing import Dict, List, Optional, Tuple, Any
from services.ssh.pool import ssh_pool
from utils.logger import get_logger

logger = get_logger()

class SSHCommandExecutor:
    """
    SSH命令执行器，提供简化的命令执行接口
    """
    
    @staticmethod
    def execute(hostname: str, port: int, username: str, 
                command: str, password: str = None, 
                ed25519_pri_file: str = None, timeout: int = 5) -> Tuple[int, str, str]:
        """
        执行SSH命令
        
        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名
            command: 要执行的命令
            password: 密码
            ed25519_pri_file: ED25519私钥文件路径
            timeout: 超时时间（秒）
            
        Returns:
            Tuple[int, str, str]: 状态码、标准输出和标准错误
        """
        client = ssh_pool.get_connection(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            ed25519_pri_file=ed25519_pri_file,
            timeout=timeout
        )
        
        # 尝试连接
        if not client.client:
            status, message = client.connect()
            if status != 0:
                return -1, "", message
        
        # 执行命令
        return client.execute_command(command, timeout=timeout)
    
    @staticmethod
    def execute_script(hostname: str, port: int, username: str, 
                       script_file: str, args: List[str] = None, 
                       password: str = None, ed25519_pri_file: str = None, 
                       timeout: int = 5) -> Tuple[int, str]:
        """
        执行SSH脚本
        
        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名
            script_file: 脚本文件路径
            args: 脚本参数
            password: 密码
            ed25519_pri_file: ED25519私钥文件路径
            timeout: 超时时间（秒）
            
        Returns:
            Tuple[int, str]: 状态码和消息
        """
        client = ssh_pool.get_connection(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            ed25519_pri_file=ed25519_pri_file,
            timeout=timeout
        )
        
        # 尝试连接
        if not client.client:
            status, message = client.connect()
            if status != 0:
                return -1, message
        
        # 执行脚本
        if args is None:
            args = []
        
        return client.ssh_exec_script(script_file, *args)
    
    @staticmethod
    def transfer_file(hostname: str, port: int, username: str, 
                      local_path: str, remote_path: str, 
                      password: str = None, ed25519_pri_file: str = None, 
                      timeout: int = 5) -> bool:
        """
        传输文件
        
        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名
            local_path: 本地文件路径
            remote_path: 远程文件路径
            password: 密码
            ed25519_pri_file: ED25519私钥文件路径
            timeout: 超时时间（秒）
            
        Returns:
            bool: 传输是否成功
        """
        client = ssh_pool.get_connection(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            ed25519_pri_file=ed25519_pri_file,
            timeout=timeout
        )
        
        # 尝试连接
        if not client.client:
            status, message = client.connect()
            if status != 0:
                logger.error(f"连接失败: {message}")
                return False
        
        # 传输文件
        return client.transfer_file(local_path, remote_path)
    
    @staticmethod
    def transfer_directory(hostname: str, port: int, username: str, 
                           local_dir: str, remote_dir: str, 
                           password: str = None, ed25519_pri_file: str = None, 
                           timeout: int = 5) -> bool:
        """
        传输目录
        
        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名
            local_dir: 本地目录路径
            remote_dir: 远程目录路径
            password: 密码
            ed25519_pri_file: ED25519私钥文件路径
            timeout: 超时时间（秒）
            
        Returns:
            bool: 传输是否成功
        """
        client = ssh_pool.get_connection(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            ed25519_pri_file=ed25519_pri_file,
            timeout=timeout
        )
        
        # 尝试连接
        if not client.client:
            status, message = client.connect()
            if status != 0:
                logger.error(f"连接失败: {message}")
                return False
        
        # 传输目录
        return client.transfer_files(local_dir, remote_dir)
