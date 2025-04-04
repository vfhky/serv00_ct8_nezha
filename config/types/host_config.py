# config/types/host_config.py
import os
from typing import Any, Dict, List, Optional, Tuple
from config.base import ConfigBase
from services.ssh.client import ParamikoClient
from utils.logger import get_logger

logger = get_logger()

class HostConfig(ConfigBase):
    """
    主机配置类，处理主机相关配置
    """

    def __init__(self, file_path: str, private_key_file: Optional[str] = None):
        self.file_path = file_path
        self.private_key_file = private_key_file
        self.config_data = {}
        self.hosts = []
        self._parse_config_file()

        # 检查配置文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"主机配置文件不存在: {file_path}")
            raise FileNotFoundError(f"主机配置文件不存在: {file_path}")

        self._init_clients()

    def _is_empty_config_file(self) -> bool:
        """
        检查配置文件是否为空或只包含注释

        Returns:
            bool: 是否为空配置文件
        """
        try:
            with open(self.file_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        return False
            return True
        except Exception:
            return False

    def _parse_config_file(self) -> None:
        """
        解析配置文件

        Raises:
            IOError: 读取配置文件错误
            ValueError: 配置文件格式错误
        """
        self.hosts = []

        if not os.path.exists(self.file_path):
            logger.warning(f"配置文件不存在: {self.file_path}")
            return

        invalid_lines = []

        try:
            with open(self.file_path, 'r') as file:
                for line_number, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('|')
                    if len(parts) != 4:
                        invalid_lines.append((line_number, line, "格式错误，应为'hostname|port|username|password'"))
                        continue

                    hostname, port, username, password = parts
                    try:
                        port_int = int(port)
                        self.hosts.append({
                            "hostname": hostname,
                            "port": port_int,
                            "username": username,
                            "password": password
                        })
                    except ValueError:
                        invalid_lines.append((line_number, line, f"端口号'{port}'不是有效的整数"))

            # 如果有无效行，记录警告
            if invalid_lines:
                for line_number, line, reason in invalid_lines:
                    logger.warning(f"配置文件 {self.file_path} 第 {line_number} 行无效: {line} - {reason}")

            logger.info(f"成功加载配置: {self.file_path}, 共 {len(self.hosts)} 个主机")
        except IOError as e:
            logger.error(f"读取配置文件错误: {self.file_path} - {str(e)}")
            raise IOError(f"读取配置文件错误: {self.file_path} - {str(e)}")

    def _init_clients(self) -> None:
        """
        初始化SSH客户端
        """
        if self.private_key_file and not os.path.exists(self.private_key_file):
            logger.warning(f"私钥文件不存在: {self.private_key_file}")

        for host_id, entry in enumerate(self.hosts, 1):
            client = self._create_client(entry, host_id)
            if client:
                entry['client'] = client

    def _create_client(self, entry: Dict[str, Any], host_id: int, timeout: int = 5) -> Optional[ParamikoClient]:
        """
        创建SSH客户端

        Args:
            entry: 主机配置条目
            host_id: 主机ID
            timeout: 超时时间

        Returns:
            Optional[ParamikoClient]: 客户端实例，如果创建失败则返回None
        """
        # 注意: 这里假设ParamikoClient已被迁移到services/ssh/client.py
        try:
            # 优先使用密钥认证
            if self.private_key_file and os.path.exists(self.private_key_file):
                client = ParamikoClient(
                    hostname=entry['hostname'],
                    port=entry['port'],
                    username=entry['username'],
                    ed25519_pri_file=self.private_key_file,
                    timeout=timeout
                )
                ret_code, ret_msg = client.connect()
                if ret_code == 0:
                    logger.info(f"====> [{host_id}] SSH密钥连接成功 {entry['username']}@{entry['hostname']}:{entry['port']}")
                    return client

            # 如果密钥认证失败或没有密钥，尝试密码认证
            if entry.get('password'):
                client = ParamikoClient(
                    hostname=entry['hostname'],
                    port=entry['port'],
                    username=entry['username'],
                    password=entry['password'],
                    timeout=timeout
                )
                ret_code, ret_msg = client.connect(use_password=True)
                if ret_code == 0:
                    logger.info(f"====> [{host_id}] SSH密码连接成功 {entry['username']}@{entry['hostname']}:{entry['port']}")
                    return client
        except Exception as e:
            logger.error(f"====> [{host_id}] 连接错误: {str(e)}")

        logger.error(f"====> [{host_id}] 连接失败 {entry['username']}@{entry['hostname']}:{entry['port']}")
        return None

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值，如果配置项不存在则返回此值

        Returns:
            Any: 配置值
        """
        return self.config_data.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置项

        Returns:
            Dict[str, Any]: 所有配置项
        """
        return {
            'hosts': self.hosts.copy(),
            **self.config_data
        }

    def get_hosts(self) -> List[Dict[str, Any]]:
        """
        获取所有主机配置

        Returns:
            List[Dict[str, Any]]: 主机配置列表
        """
        return self.hosts.copy()

    def reload(self) -> bool:
        """
        重新加载配置

        Returns:
            bool: 重新加载是否成功
        """
        try:
            self._parse_config_file()
            logger.info(f"成功重新加载配置: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {self.file_path}: {str(e)}")
            return False

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证配置

        Returns:
            Tuple[bool, List[str]]: 验证是否通过和错误消息列表
        """
        errors = []

        # 验证主机配置
        for i, host in enumerate(self.hosts):
            if 'hostname' not in host:
                errors.append(f"主机 {i+1} 缺少 hostname")
            if 'port' not in host:
                errors.append(f"主机 {i+1} 缺少 port")
            elif not isinstance(host['port'], int):
                errors.append(f"主机 {i+1} 的 port 必须为整数")
            elif host['port'] < 1 or host['port'] > 65535:
                errors.append(f"主机 {i+1} 的 port 必须在1-65535之间")
            if 'username' not in host:
                errors.append(f"主机 {i+1} 缺少 username")
            if 'password' not in host:
                errors.append(f"主机 {i+1} 缺少 password")

        return len(errors) == 0, errors