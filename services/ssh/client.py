import os
import paramiko
from typing import Optional, Tuple, List, Dict, Any, Callable
from utils.logger import get_logger
from services.ssh.base import SSHClientBase

logger = get_logger()

class ParamikoClient(SSHClientBase):
    """
    基于Paramiko的SSH客户端实现
    """
    
    def __init__(self, hostname: str, port: int = 22, username: str = None, 
                 password: str = None, ed25519_pri_file: str = None, timeout: int = 5):
        """
        初始化SSH客户端
        
        Args:
            hostname: 主机名
            port: 端口号
            username: 用户名
            password: 密码
            ed25519_pri_file: ED25519私钥文件路径
            timeout: 超时时间（秒）
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ed25519_pri_file = ed25519_pri_file
        self.timeout = timeout
        self.client = None
        self.additional_options = {}

    def __del__(self):
        self.cleanup()
    
    def connect(self, use_password: bool = False, **kwargs) -> Tuple[int, str]:
        """
        建立SSH连接
        
        Args:
            use_password: 是否使用密码认证
            **kwargs: 其他连接参数
            
        Returns:
            Tuple[int, str]: 状态码和消息
        """
        connect_type = "password" if use_password else "key"
        return self._connect(connect_type, **kwargs)
    
    def _connect(self, connect_type: str, **kwargs) -> Tuple[int, str]:
        """
        内部连接方法
        
        Args:
            connect_type: 连接类型，"password" 或 "key"
            **kwargs: 其他连接参数
            
        Returns:
            Tuple[int, str]: 状态码和消息
        """
        if not self.client:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_params = {
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'timeout': self.timeout,
            **self.additional_options,
            **kwargs  # 允许在调用时覆盖默认参数
        }

        try:
            if connect_type == 'password':
                connect_params['password'] = self.password
            else:
                if not self.ed25519_pri_file or not os.path.exists(self.ed25519_pri_file):
                    return -3, f"====> 密钥文件未找到: {self.ed25519_pri_file} [{self.username}@{self.hostname}:{self.port}]"
                
                pkey = paramiko.Ed25519Key(filename=self.ed25519_pri_file)
                connect_params['pkey'] = pkey

            self.client.connect(**connect_params)
            return 0, f"====> 连接成功 [{self.username}@{self.hostname}:{self.port}]"
        except paramiko.ssh_exception.AuthenticationException:
            return -1, f"====> 认证失败，请检查用户名和密码/密钥 [{self.username}@{self.hostname}:{self.port}]"
        except paramiko.ssh_exception.SSHException as ssh_error:
            return -2, f"====> SSH异常: {ssh_error} [{self.username}@{self.hostname}:{self.port}]"
        except Exception as e:
            return -4, f"====> 连接失败，错误信息: {e} [{self.username}@{self.hostname}:{self.port}]"
    
    def execute_command(self, command: str, **kwargs) -> Tuple[int, str, str]:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            **kwargs: 其他参数
            
        Returns:
            Tuple[int, str, str]: 状态码、标准输出和标准错误
        """
        if not self.client:
            return -1, "", f"SSH client not connected [{self.username}@{self.hostname}:{self.port}]"
        
        try:
            timeout = kwargs.get('timeout', self.timeout)
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()

            stdout_output = stdout.read().decode()
            stderr_output = stderr.read().decode()

            logger.debug(f"命令执行结果: {command}\nSTDOUT: {stdout_output}\nSTDERR: {stderr_output}")
            
            return exit_status, stdout_output, stderr_output
        except Exception as e:
            error_message = f"执行命令失败: {command}, 错误: {str(e)}"
            logger.error(error_message)
            return -1, "", error_message
    
    def transfer_file(self, local_path: str, remote_path: str) -> bool:
        """
        传输单个文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            
        Returns:
            bool: 传输是否成功
        """
        if not self.client:
            logger.error(f"SSH client not connected [{self.username}@{self.hostname}:{self.port}]")
            return False
        
        try:
            with self.client.open_sftp() as sftp:
                # 确保远程目录存在
                remote_dir = os.path.dirname(remote_path)
                self.ensure_remote_dir_exists(sftp, remote_dir)
                
                # 传输文件
                sftp.put(local_path, remote_path)
                
                # 保持权限
                local_mode = os.stat(local_path).st_mode
                sftp.chmod(remote_path, local_mode)
                
                logger.info(f"====> 文件传输成功: {local_path} -> [{self.username}@{self.hostname}:{self.port}]:{remote_path}")
                return True
        except Exception as e:
            logger.error(f"文件传输失败: {local_path} -> [{self.username}@{self.hostname}:{self.port}]:{remote_path}, 错误: {str(e)}")
            return False
    
    def transfer_files(self, local_dir: str, remote_dir: str) -> bool:
        """
        传输目录中的所有文件
        
        Args:
            local_dir: 本地目录路径
            remote_dir: 远程目录路径
            
        Returns:
            bool: 传输是否成功
        """
        if not self.client:
            logger.error(f"SSH client not connected [{self.username}@{self.hostname}:{self.port}]")
            return False
        
        try:
            with self.client.open_sftp() as sftp:
                self.ensure_remote_dir_exists(sftp, remote_dir)
                logger.info(f"==> 开始拷贝[{local_dir}]目录到远程主机[{self.username}@{self.hostname}:{self.port}] [{remote_dir}]")
                
                success = True
                for root, _, files in os.walk(local_dir):
                    for file in files:
                        local_file = os.path.join(root, file)
                        relative_path = os.path.relpath(local_file, local_dir)
                        remote_file = os.path.join(remote_dir, relative_path)

                        self.ensure_remote_dir_exists(sftp, os.path.dirname(remote_file))
                        try:
                            sftp.put(local_file, remote_file, callback=lambda transferred, total: 
                                    logger.debug(f"传输进度: {local_file} {transferred}/{total} bytes"))
                            local_mode = os.stat(local_file).st_mode
                            sftp.chmod(remote_file, local_mode)
                            logger.info(f"====> 拷贝文件成功: {local_file} -> [{self.username}@{self.hostname}:{self.port}]:{remote_file}")
                        except Exception as file_e:
                            logger.error(f"拷贝文件失败: {local_file} -> [{self.username}@{self.hostname}:{self.port}]:{remote_file}, 错误: {str(file_e)}")
                            success = False
                
                return success
        except Exception as e:
            logger.error(f"文件传输失败: {local_dir} -> [{self.username}@{self.hostname}:{self.port}]:{remote_dir}, 错误: {str(e)}")
            return False
    
    def ensure_remote_dir_exists(self, sftp, remote_dir: str) -> None:
        """
        确保远程目录存在，不存在则创建
        
        Args:
            sftp: SFTP客户端
            remote_dir: 远程目录路径
        """
        dirs = remote_dir.split('/')
        current_dir = ''
        for dir in dirs:
            if dir:
                current_dir = f"{current_dir}/{dir}"
                try:
                    sftp.stat(current_dir)
                except FileNotFoundError:
                    sftp.mkdir(current_dir)
                    logger.debug(f"====> 创建远程目录: [{self.username}@{self.hostname}:{self.port}]:{current_dir}")
    
    def ssh_exec_script(self, script_file: str, *args: str) -> Tuple[int, str]:
        """
        执行远程脚本
        
        Args:
            script_file: 脚本文件路径
            *args: 脚本参数
            
        Returns:
            Tuple[int, str]: 状态码和消息
        """
        if not self.client:
            return -1, f"SSH client not connected [{self.username}@{self.hostname}:{self.port}]"
        
        try:
            from utils.system import get_shell_run_cmd
            cmd = get_shell_run_cmd(script_file, *args)
            logger.info(f"==> 执行远程命令 [{self.username}@{self.hostname}:{self.port}]: {cmd}")
            
            exit_status, stdout, stderr = self.execute_command(cmd)
            
            if exit_status == 0:
                ret_msg = f'通过SSH执行 {cmd} 命令成功 [{self.username}@{self.hostname}:{self.port}]'
                logger.info(ret_msg)
                return 0, ret_msg
            else:
                ret_msg = f'通过SSH执行 {cmd} 命令时出错，退出状态码: {exit_status} [{self.username}@{self.hostname}:{self.port}]'
                logger.error(ret_msg)
                return -1, ret_msg
        except Exception as e:
            error_message = f"执行脚本失败 [{self.username}@{self.hostname}:{self.port}]: {str(e)}"
            logger.error(error_message)
            return -2, error_message
    
    def close(self) -> None:
        """
        关闭连接
        """
        if self.client:
            self.client.close()
            self.client = None
            logger.info(f"关闭SSH连接 [{self.username}@{self.hostname}:{self.port}]")

    def cleanup(self) -> None:
        """
        清理资源，关闭连接
        """
        if self.client:
            try:
                self.client.close()
                logger.debug(f"SSH连接已关闭: {self.username}@{self.hostname}:{self.port}")
            except Exception as e:
                logger.error(f"关闭SSH连接异常: {str(e)}")
            finally:
                self.client = None
