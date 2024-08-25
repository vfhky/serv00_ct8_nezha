import os
from typing import List, Dict, Optional
from paramiko_client import ParamikoClient
from logger_wrapper import LoggerWrapper

# 初始化日志记录器
logger = LoggerWrapper()

class HeartBeatConfigEntry:
    def __init__(self, file_path: str, private_key_file: Optional[str] = None):
        self.config_entries: List[Dict[str, any]] = self.parse_config_file(file_path)
        self.private_key_file: Optional[str] = private_key_file
        self.init_clients()

    def __repr__(self) -> str:
        return f"HeartBeatConfigEntry(config_entries={self.config_entries})"

    @staticmethod
    def parse_config_file(file_path: str) -> List[Dict[str, any]]:
        config_entries = []
        try:
            with open(file_path, 'r') as file:
                for line_number, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) != 3:
                        logger.warning(f"Skipping invalid line {line_number}: {line}")
                        continue
                    hostname, port, username = parts
                    try:
                        config_entries.append({
                            "hostname": hostname,
                            "port": int(port),
                            "username": username
                        })
                    except ValueError:
                        logger.warning(f"Invalid port number on line {line_number}: {line}")
        except IOError as e:
            logger.error(f"Error reading config file: {e}")
        return config_entries

    def init_clients(self) -> None:
        if self.private_key_file and not os.path.exists(self.private_key_file):
            logger.warning(f"Private key file not found: {self.private_key_file}")
        for host_id, entry in enumerate(self.config_entries, 1):
            client = self.create_client(entry, host_id)
            if client:
                entry['client'] = client

    def create_client(self, entry: Dict[str, any], host_id: int, timeout: int = 2) -> Optional[ParamikoClient]:
        if self.private_key_file and os.path.exists(self.private_key_file):
            try:
                client = ParamikoClient(
                    hostname=entry['hostname'],
                    port=entry['port'],
                    username=entry['username'],
                    ed25519_pri_file=self.private_key_file,
                    timeout=timeout
                )
                ret_code, ret_msg = client.sshd_connect()
                if ret_code == 0:
                    logger.info(f"====> [{host_id}] SSH key connect OK {entry['username']}@{entry['hostname']}:{entry['port']}")
                    return client
            except Exception as e:
                logger.error(f"====> [{host_id}] Connection error: {str(e)}")
        
        logger.error(f"====> [{host_id}] Connect fail {entry['username']}@{entry['hostname']}:{entry['port']} SSH key={self.private_key_file}")
        return None

    def get_entries(self) -> List[Dict[str, any]]:
        return self.config_entries
