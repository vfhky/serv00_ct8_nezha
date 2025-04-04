import os
from typing import Optional, Tuple, List, Dict, Any
from services.ssh.pool import ssh_pool
from services.ssh.command import SSHCommandExecutor
from config.base import ConfigBase
from utils.logger import get_logger
from utils.decorators import singleton

logger = get_logger()

@singleton
class SSHHelper:
    """
    SSH连接助手，提供更高级的SSH操作
    """

    def __init__(self):
        self.config = None

    def initialize(self, config: ConfigBase) -> None:
        """
        初始化SSH连接助手

        Args:
            config: 配置实例
        """
        self.config = config

    def connect_from_config(self, host_id: str, use_password: bool = False) -> Tuple[int, str]:
        """
        从配置连接到主机

        Args:
            host_id: 主机ID
            use_password: 是否使用密码认证

        Returns:
            Tuple[int, str]: 状态码和消息
        """
        if not self.config:
            return -1, "SSH连接助手未初始化"

        # 从配置中获取主机信息
        # 注意: 这里假设配置中有主机列表
        hosts = self.config.get('SSH_HOSTS', [])
        host = next((h for h in hosts if h.get('id') == host_id), None)

        if not host:
            return -1, f"未找到主机: {host_id}"

        hostname = host.get('hostname')
        port = int(host.get('port', 22))
        username = host.get('username')
        password = host.get('password')
        key_file = host.get('key_file')

        client = ssh_pool.get_connection(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            ed25519_pri_file=key_file
        )

        return client.connect(use_password=use_password)

    def execute_on_all_hosts(self, command: str) -> Dict[str, Tuple[int, str, str]]:
        """
        在所有主机上执行命令

        Args:
            command: 要执行的命令

        Returns:
            Dict[str, Tuple[int, str, str]]: 主机ID到执行结果的映射
        """
        if not self.config:
            logger.error("SSH连接助手未初始化")
            return {}

        results = {}
        hosts = self.config.get('SSH_HOSTS', [])

        for host in hosts:
            host_id = host.get('id')
            hostname = host.get('hostname')
            port = int(host.get('port', 22))
            username = host.get('username')
            password = host.get('password')
            key_file = host.get('key_file')

            try:
                result = SSHCommandExecutor.execute(
                    hostname=hostname,
                    port=port,
                    username=username,
                    command=command,
                    password=password,
                    ed25519_pri_file=key_file
                )
                results[host_id] = result
            except Exception as e:
                logger.error(f"在主机 {host_id} 上执行命令失败: {str(e)}")
                results[host_id] = (-1, "", str(e))

        return results

    def check_host_status(self, host_id: str) -> bool:
        """
        检查主机状态

        Args:
            host_id: 主机ID

        Returns:
            bool: 主机是否在线
        """
        if not self.config:
            logger.error("SSH连接助手未初始化")
            return False

        # 从配置中获取主机信息
        hosts = self.config.get('SSH_HOSTS', [])
        host = next((h for h in hosts if h.get('id') == host_id), None)

        if not host:
            logger.error(f"未找到主机: {host_id}")
            return False

        hostname = host.get('hostname')
        port = int(host.get('port', 22))
        username = host.get('username')
        password = host.get('password')
        key_file = host.get('key_file')

        try:
            client = ssh_pool.get_connection(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                ed25519_pri_file=key_file,
                timeout=3
            )

            status, _ = client.connect()
            return status == 0
        except Exception:
            return False

# 创建单例实例
ssh_helper = SSHHelper()
