# services/ssh/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

class SSHClientBase(ABC):
    """
    SSH客户端基类，定义了SSH操作的基本接口
    """
    
    @abstractmethod
    def connect(self, **kwargs: Any) -> Tuple[int, str]:
        """
        建立连接
        
        Args:
            **kwargs: 连接参数
            
        Returns:
            Tuple[int, str]: 状态码和消息
        """
        pass
    
    @abstractmethod
    def execute_command(self, command: str, **kwargs: Any) -> Tuple[int, str, str]:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            **kwargs: 其他参数
            
        Returns:
            Tuple[int, str, str]: 状态码、标准输出和标准错误
        """
        pass
    
    @abstractmethod
    def transfer_file(self, local_path: str, remote_path: str) -> bool:
        """
        传输文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            
        Returns:
            bool: 传输是否成功
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭连接
        """
        pass