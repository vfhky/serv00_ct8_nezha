import time
from typing import Dict, Optional, Tuple, List, Any
from services.ssh.client import ParamikoClient
from utils.logger import get_logger
from utils.decorators import singleton

logger = get_logger()

@singleton
class SSHConnectionPool:
    """
    SSH连接池，管理SSH连接
    """
    def __init__(self):
        self.connections: Dict[str, ParamikoClient] = {}
        self.last_used: Dict[str, float] = {}
        self.max_idle_time = 3600  # 1小时

    def get_connection_key(self, hostname: str, port: int, username: str) -> str:
        """
        获取连接键

        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名

        Returns:
            str: 连接键
        """
        return f"{username}@{hostname}:{port}"

    def get_connection(self, hostname: str, port: int = 22, username: str = None,
                       password: str = None, ed25519_pri_file: str = None,
                       reuse: bool = True, timeout: int = 5) -> ParamikoClient:
        """
        获取SSH连接

        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名
            password: 密码
            ed25519_pri_file: ED25519私钥文件路径
            reuse: 是否重用连接
            timeout: 超时时间（秒）

        Returns:
            ParamikoClient: SSH客户端实例
        """
        key = self.get_connection_key(hostname, port, username)

        # 清理过期连接
        self._cleanup_idle_connections()

        # 检查是否有可重用的连接
        if reuse and key in self.connections:
            logger.info(f"重用SSH连接: {key}")
            self.last_used[key] = time.time()
            return self.connections[key]

        # 创建新连接
        client = ParamikoClient(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            ed25519_pri_file=ed25519_pri_file,
            timeout=timeout
        )

        # 存储连接
        self.connections[key] = client
        self.last_used[key] = time.time()

        return client

    def release_connection(self, hostname: str, port: int, username: str) -> None:
        """
        释放连接

        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名
        """
        key = self.get_connection_key(hostname, port, username)
        if key in self.connections:
            client = self.connections.pop(key)
            if key in self.last_used:
                del self.last_used[key]

            client.close()
            logger.info(f"释放SSH连接: {key}")

    def _cleanup_idle_connections(self) -> None:
        """
        清理空闲连接
        """
        current_time = time.time()
        keys_to_remove = []

        for key, last_used_time in self.last_used.items():
            if current_time - last_used_time > self.max_idle_time:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            client = self.connections.pop(key, None)
            if client:
                client.close()

            del self.last_used[key]
            logger.info(f"清理空闲SSH连接: {key}")

    def close_all(self) -> None:
        """
        关闭所有连接
        """
        for key, client in self.connections.items():
            client.close()

        self.connections.clear()
        self.last_used.clear()
        logger.info("关闭所有SSH连接")

# 创建单例实例
ssh_pool = SSHConnectionPool()
