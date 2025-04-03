# This file is intentionally left empty to mark directory as Python package

from services.ssh.base import SSHClientBase
from services.ssh.client import ParamikoClient
from services.ssh.pool import SSHConnectionPool, ssh_pool
from services.ssh.command import SSHCommandExecutor

# 导出简化接口
execute_command = SSHCommandExecutor.execute
execute_script = SSHCommandExecutor.execute_script
transfer_file = SSHCommandExecutor.transfer_file
transfer_directory = SSHCommandExecutor.transfer_directory
get_connection = ssh_pool.get_connection
release_connection = ssh_pool.release_connection
close_all_connections = ssh_pool.close_all

__all__ = [
    'SSHClientBase',
    'ParamikoClient',
    'SSHConnectionPool',
    'ssh_pool',
    'SSHCommandExecutor',
    'execute_command',
    'execute_script',
    'transfer_file',
    'transfer_directory',
    'get_connection',
    'release_connection',
    'close_all_connections'
]
