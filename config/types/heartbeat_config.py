# config/types/heartbeat_config.py
import os
from typing import Any, Dict, List, Optional
from config.base import ConfigBase
from services.ssh.paramiko_client import ParamikoClient
from utils.logger import get_logger

logger = get_logger()

class HeartbeatConfig(ConfigBase):
    """
    心跳配置类，处理心跳相关配置
    """
    
    def __init__(self, file_path: str, private_key_file: Optional[str] = None):
        self.file_path = file_path
        self.private_key_file = private_key_file
        self.config_entries = self._parse_config_file()
        self._init_clients()
    
    def _parse_config_file(self) -> List[Dict[str, Any]]:
        """
        解析配置文件
        
        Returns:
            List[Dict[str, Any]]: 配置字典列表
        """
        config_entries = []
        try:
            with open(self.file_path, 'r') as file:
                for line_number, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) != 3:
                        logger.warning(f"跳过无效行 {line_number}: {line}")
                        continue
                    hostname, port, username = parts
                    try:
                        config_entries.append({
                            "hostname": hostname,
                            "port": int(port),
                            "username": username
                        })
                    except ValueError:
                        logger.warning(f"无效的端口号，行 {line_number}: {line}")
        except IOError as e:
            logger.error(f"读取配置文件错误: {e}")
        return config_entries
    
    def _init_clients(self) -> None:
        """
        初始化SSH客户端
        """
        if self.private_key_file and not os.path.exists(self.private_key_file):
            logger.warning(f"私钥文件不存在: {self.private_key_file}")
        
        for host_id, entry in enumerate(self.config_entries, 1):
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
        if self.private_key_file and os.path.exists(self.private_key_file):
            try:
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
            except Exception as e:
                logger.error(f"====> [{host_id}] 连接错误: {str(e)}")
        
        logger.error(f"====> [{host_id}] 连接失败 {entry['username']}@{entry['hostname']}:{entry['port']} SSH密钥={self.private_key_file}")
        return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值 (不适用于此配置类型，返回None)
        """
        return None
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            Dict[str, Any]: 配置的字典表示
        """
        return {"entries": self.config_entries}
    
    def get_entries(self) -> List[Dict[str, Any]]:
        """
        获取所有主机条目
        
        Returns:
            List[Dict[str, Any]]: 主机条目列表
        """
        return self.config_entries
    
    def reload(self) -> None:
        """
        重新加载配置
        """
        self.config_entries = self._parse_config_file()
        self._init_clients()