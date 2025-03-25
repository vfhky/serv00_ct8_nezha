from paramiko_client import ParamikoClient
import os
from typing import List, Dict, Optional
from logger_wrapper import LoggerWrapper

# 初始化日志记录器
logger = LoggerWrapper()

class HostConfigEntry:
    def __init__(self, file_path: str, private_key_file: Optional[str] = None, timeout: int = 3):
        self.config_entries = self.parse_config_file(file_path)
        self.private_key_file = private_key_file
        self.timeout = timeout
        self.init_clients()

    def __repr__(self) -> str:
        return f"HostConfigEntry(config_entries={self.config_entries})"

    @staticmethod
    def parse_config_file(file_path: str) -> List[Dict[str, str]]:
        config_entries = []
        try:
            with open(file_path, 'r') as file:
                for line_number, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) != 4:
                        logger.warning(f"Skipping invalid line {line_number}: {line}")
                        continue
                    hostname, port, username, password = parts
                    try:
                        config_entries.append({
                            "hostname": hostname,
                            "port": int(port),
                            "username": username,
                            "password": password
                        })
                    except ValueError:
                        logger.warning(f"Invalid port number on line {line_number}: {line}")
        except IOError as e:
            logger.error(f"Error reading config file: {e}")
        return config_entries

    def init_clients(self) -> None:
        for host_id, entry in enumerate(self.config_entries, 1):
            client = self.create_client(entry, host_id)
            entry['client'] = client

    def create_client(self, entry: Dict[str, str], host_id: int) -> Optional[ParamikoClient]:
        client = None
        if entry['password']:
            client = self.try_connection(entry, host_id, use_password=True)
        
        if not client and self.private_key_file and os.path.exists(self.private_key_file):
            client = self.try_connection(entry, host_id, use_password=False)
        
        if not client:
            logger.error(f"====> [{host_id}] Failed to connect to {entry['username']}@{entry['hostname']} with either password or SSH key.")
        
        return client

    def try_connection(self, entry: Dict[str, str], host_id: int, use_password: bool) -> Optional[ParamikoClient]:
        client_params = {
            "hostname": entry['hostname'],
            "port": entry['port'],
            "username": entry['username'],
            "timeout": self.timeout
        }
        
        if use_password:
            client_params["password"] = entry['password']
            connection_method = "password_connect"
            connection_type = "Password-based"
        else:
            client_params["ed25519_pri_file"] = self.private_key_file
            connection_method = "sshd_connect"
            connection_type = "SSH key-based"

        try:
            client = ParamikoClient(**client_params)
            ret_code, _ = getattr(client, connection_method)()
            if ret_code == 0:
                logger.info(f"====> [{host_id}] {connection_type} connection successful for {entry['username']}@{entry['hostname']}")
                return client
        except Exception as e:
            logger.error(f"====> [{host_id}] {connection_type} connection failed for {entry['username']}@{entry['hostname']}: {str(e)}")
        
        return None

    def get_entries(self) -> List[Dict[str, str]]:
        return self.config_entries
