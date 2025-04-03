# cli/handler.py (仅显示需要修改的导入部分)

import os
import sys
import json
import yaml
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.service_manager import service_manager
from services.installer.factory import InstallerFactory
from services.installer import dashboard_installer, agent_installer

logger = get_logger()

class CommandHandler:
    """
    命令行命令处理器
    """
    
    def __init__(self, debug: bool = False, config_file: Optional[str] = None):
        """
        初始化命令处理器
        
        Args:
            debug: 是否启用调试模式
            config_file: 配置文件路径
        """
        # 设置日志级别
        if debug:
            setup_logger(logging.DEBUG)
        else:
            setup_logger(logging.INFO)
        
        # 初始化服务管理器
        self.initialized = service_manager.initialize(config_file)
    
    def handle_install_dashboard(self, args: Dict[str, Any]) -> int:
        """
        处理安装哪吒面板命令
        
        Args:
            args: 命令参数
            
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        # 准备配置参数
        config_params = {}
        
        if args.get('http_port'):
            config_params['HTTPPort'] = args['http_port']
        
        if args.get('grpc_port'):
            config_params['GRPCPort'] = args['grpc_port']
        
        if args.get('grpc_host'):
            config_params['GRPCHost'] = args['grpc_host']
        
        if args.get('site_title'):
            config_params['SiteBrand'] = args['site_title']
        
        if args.get('admin'):
            config_params['OAuth2Admin'] = args['admin']
        
        if args.get('github_oauth_client_id'):
            config_params['OAuth2ClientID'] = args['github_oauth_client_id']
        
        if args.get('github_oauth_client_secret'):
            config_params['OAuth2ClientSecret'] = args['github_oauth_client_secret']
        
        # 执行安装
        version = args.get('version', 'v0')
        
        # 创建dashboard安装器
        from core.installer.factory import InstallerFactory
        dashboard_installer = InstallerFactory.create_dashboard_installer(
            service_manager.config, 
            version
        )
        
        # 安装Dashboard
        success, message = service_manager.install_dashboard(config_params)
        
        if success:
            print(f"安装哪吒面板成功: {message}")
            return 0
        else:
            print(f"安装哪吒面板失败: {message}")
            return 1
    
    def handle_install_agent(self, args: Dict[str, Any]) -> int:
        """
        处理安装哪吒探针命令
        
        Args:
            args: 命令参数
            
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        # 执行安装
        version = args.get('version', 'v0')
        server = args.get('server')
        key = args.get('key')
        
        if not server or not key:
            print("错误: 必须提供服务器地址和密钥")
            return 1
        
        # 创建agent安装器
        from core.installer.factory import InstallerFactory
        agent_installer = InstallerFactory.create_agent_installer(
            service_manager.config, 
            version
        )
        
        # 安装Agent
        success, message = service_manager.install_agent(server, key)
        
        if success:
            print(f"安装哪吒探针成功: {message}")
            return 0
        else:
            print(f"安装哪吒探针失败: {message}")
            return 1
    
    def handle_uninstall_dashboard(self) -> int:
        """
        处理卸载哪吒面板命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        success, message = service_manager.uninstall_dashboard()
        
        if success:
            print(f"卸载哪吒面板成功: {message}")
            return 0
        else:
            print(f"卸载哪吒面板失败: {message}")
            return 1
    
    def handle_uninstall_agent(self) -> int:
        """
        处理卸载哪吒探针命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        success, message = service_manager.uninstall_agent()
        
        if success:
            print(f"卸载哪吒探针成功: {message}")
            return 0
        else:
            print(f"卸载哪吒探针失败: {message}")
            return 1
    
    def handle_start_dashboard(self) -> int:
        """
        处理启动哪吒面板命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import dashboard_installer
        success, message = dashboard_installer.start()
        
        if success:
            print(f"启动哪吒面板成功: {message}")
            return 0
        else:
            print(f"启动哪吒面板失败: {message}")
            return 1
    
    def handle_start_agent(self) -> int:
        """
        处理启动哪吒探针命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import agent_installer
        success, message = agent_installer.start()
        
        if success:
            print(f"启动哪吒探针成功: {message}")
            return 0
        else:
            print(f"启动哪吒探针失败: {message}")
            return 1
    
    def handle_start_all(self) -> int:
        """
        处理启动所有服务命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        success = service_manager.start_services()
        
        if success:
            print("启动所有服务成功")
            return 0
        else:
            print("启动所有服务失败")
            return 1
    
    def handle_stop_dashboard(self) -> int:
        """
        处理停止哪吒面板命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import dashboard_installer
        success, message = dashboard_installer.stop()
        
        if success:
            print(f"停止哪吒面板成功: {message}")
            return 0
        else:
            print(f"停止哪吒面板失败: {message}")
            return 1
    
    def handle_stop_agent(self) -> int:
        """
        处理停止哪吒探针命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import agent_installer
        success, message = agent_installer.stop()
        
        if success:
            print(f"停止哪吒探针成功: {message}")
            return 0
        else:
            print(f"停止哪吒探针失败: {message}")
            return 1
    
    def handle_stop_all(self) -> int:
        """
        处理停止所有服务命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        success = service_manager.stop_services()
        
        if success:
            print("停止所有服务成功")
            return 0
        else:
            print("停止所有服务失败")
            return 1
    
    def handle_restart_dashboard(self) -> int:
        """
        处理重启哪吒面板命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import dashboard_installer
        
        # 先停止
        success, _ = dashboard_installer.stop()
        if not success:
            print("停止哪吒面板失败")
            return 1
        
        # 再启动
        success, message = dashboard_installer.start()
        
        if success:
            print(f"重启哪吒面板成功: {message}")
            return 0
        else:
            print(f"重启哪吒面板失败: {message}")
            return 1
    
    def handle_restart_agent(self) -> int:
        """
        处理重启哪吒探针命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import agent_installer
        
        # 先停止
        success, _ = agent_installer.stop()
        if not success:
            print("停止哪吒探针失败")
            return 1
        
        # 再启动
        success, message = agent_installer.start()
        
        if success:
            print(f"重启哪吒探针成功: {message}")
            return 0
        else:
            print(f"重启哪吒探针失败: {message}")
            return 1
    
    def handle_restart_all(self) -> int:
        """
        处理重启所有服务命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        success = service_manager.restart_services()
        
        if success:
            print("重启所有服务成功")
            return 0
        else:
            print("重启所有服务失败")
            return 1
    
    def handle_status_dashboard(self) -> int:
        """
        处理查看哪吒面板状态命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import dashboard_installer
        
        is_running, message = dashboard_installer.check_status()
        version = dashboard_installer.get_version()
        
        status = {
            "installed": version is not None,
            "running": is_running,
            "version": version,
            "message": message
        }
        
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0
    
    def handle_status_agent(self) -> int:
        """
        处理查看哪吒探针状态命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import agent_installer
        
        is_running, message = agent_installer.check_status()
        version = agent_installer.get_version()
        
        status = {
            "installed": version is not None,
            "running": is_running,
            "version": version,
            "message": message
        }
        
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0
    
    def handle_status_all(self) -> int:
        """
        处理查看所有服务状态命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        status = service_manager.get_service_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0
    
    def handle_backup(self, args: Dict[str, Any]) -> int:
        """
        处理备份服务配置命令
        
        Args:
            args: 命令参数
            
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        # 获取备份目标路径
        target_path = args.get('target')
        
        # 获取配置文件列表
        config_files = []
        
        # 获取哪吒面板配置文件
        from utils.system import get_dashboard_config_file
        import getpass
        dashboard_config = get_dashboard_config_file(getpass.getuser())
        if os.path.exists(dashboard_config):
            config_files.append(dashboard_config)
        
        # 获取哪吒探针配置文件
        from utils.system import get_agent_config_file
        agent_config = get_agent_config_file(getpass.getuser())
        if os.path.exists(agent_config):
            config_files.append(agent_config)
        
        # 备份配置文件
        success = service_manager.backup_files(config_files, "nezha_config_backup")
        
        if success:
            print("备份服务配置成功")
            return 0
        else:
            print("备份服务配置失败")
            return 1
    
    def handle_update_dashboard(self) -> int:
        """
        处理更新哪吒面板命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import dashboard_installer
        
        # 获取当前状态
        is_running, _ = dashboard_installer.check_status()
        
        # 先停止服务
        if is_running:
            dashboard_installer.stop()
        
        # 执行下载
        success, message = dashboard_installer.download()
        if not success:
            print(f"更新哪吒面板失败: {message}")
            return 1
        
        # 安装
        success, message = dashboard_installer.install()
        if not success:
            print(f"更新哪吒面板失败: {message}")
            return 1
        
        # 如果之前是运行状态，则重新启动
        if is_running:
            success, message = dashboard_installer.start()
            if not success:
                print(f"启动哪吒面板失败: {message}")
                return 1
        
        print("更新哪吒面板成功")
        return 0
    
    def handle_update_agent(self) -> int:
        """
        处理更新哪吒探针命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        from core.installer import agent_installer
        
        # 获取当前状态
        is_running, _ = agent_installer.check_status()
        
        # 先停止服务
        if is_running:
            agent_installer.stop()
        
        # 执行下载
        success, message = agent_installer.download()
        if not success:
            print(f"更新哪吒探针失败: {message}")
            return 1
        
        # 安装
        success, message = agent_installer.install()
        if not success:
            print(f"更新哪吒探针失败: {message}")
            return 1
        
        # 如果之前是运行状态，则重新启动
        if is_running:
            success, message = agent_installer.start()
            if not success:
                print(f"启动哪吒探针失败: {message}")
                return 1
        
        print("更新哪吒探针成功")
        return 0
    
    def handle_update_all(self) -> int:
        """
        处理更新所有服务命令
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        # 先更新哪吒面板
        status1 = self.handle_update_dashboard()
        
        # 再更新哪吒探针
        status2 = self.handle_update_agent()
        
        if status1 == 0 and status2 == 0:
            print("更新所有服务成功")
            return 0
        else:
            print("更新服务过程中出现错误")
            return 1
    
    def handle_logs_dashboard(self, args: Dict[str, Any]) -> int:
        """
        处理查看哪吒面板日志命令
        
        Args:
            args: 命令参数
            
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        lines = args.get('lines', 100)
        
        # 获取哪吒面板日志路径
        log_file = "/tmp/nezha-dashboard.log"
        
        if os.path.exists(log_file):
            code, stdout, _ = run_shell_command(f"tail -n {lines} {log_file}")
            if code == 0:
                print(stdout)
                return 0
            else:
                print(f"读取日志失败: {log_file}")
                return 1
        else:
            print(f"日志文件不存在: {log_file}")
            return 1
    
    def handle_logs_agent(self, args: Dict[str, Any]) -> int:
        """
        处理查看哪吒探针日志命令
        
        Args:
            args: 命令参数
            
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        lines = args.get('lines', 100)
        
        # 获取哪吒探针日志路径
        log_file = "/tmp/nezha-agent.log"
        
        if os.path.exists(log_file):
            code, stdout, _ = run_shell_command(f"tail -n {lines} {log_file}")
            if code == 0:
                print(stdout)
                return 0
            else:
                print(f"读取日志失败: {log_file}")
                return 1
        else:
            print(f"日志文件不存在: {log_file}")
            return 1
    
    def handle_logs_system(self, args: Dict[str, Any]) -> int:
        """
        处理查看系统日志命令
        
        Args:
            args: 命令参数
            
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        lines = args.get('lines', 100)
        
        # 获取系统日志路径
        import tempfile
        temp_dir = tempfile.gettempdir()
        log_file = os.path.join(temp_dir, "nezha_manager.log")
        
        if os.path.exists(log_file):
            code, stdout, _ = run_shell_command(f"tail -n {lines} {log_file}")
            if code == 0:
                print(stdout)
                return 0
            else:
                print(f"读取日志失败: {log_file}")
                return 1
        else:
            print(f"日志文件不存在: {log_file}")
            return 1
    
    def handle_command(self, args: Dict[str, Any]) -> int:
        """
        处理命令
        
        Args:
            args: 命令参数
            
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        if not self.initialized:
            print("错误: 服务管理器初始化失败")
            return 1
        
        command = args.get('command')
        
        if command == 'install':
            install_type = args.get('install_type')
            
            if install_type == 'dashboard':
                return self.handle_install_dashboard(args)
            elif install_type == 'agent':
                return self.handle_install_agent(args)
            else:
                print("错误: 请指定安装类型")
                return 1
        
        elif command == 'uninstall':
            uninstall_type = args.get('uninstall_type')
            
            if uninstall_type == 'dashboard':
                return self.handle_uninstall_dashboard()
            elif uninstall_type == 'agent':
                return self.handle_uninstall_agent()
            else:
                print("错误: 请指定卸载类型")
                return 1
        
        elif command == 'start':
            start_type = args.get('start_type')
            
            if start_type == 'dashboard':
                return self.handle_start_dashboard()
            elif start_type == 'agent':
                return self.handle_start_agent()
            elif start_type == 'all':
                return self.handle_start_all()
            else:
                print("错误: 请指定启动类型")
                return 1
        
        elif command == 'stop':
            stop_type = args.get('stop_type')
            
            if stop_type == 'dashboard':
                return self.handle_stop_dashboard()
            elif stop_type == 'agent':
                return self.handle_stop_agent()
            elif stop_type == 'all':
                return self.handle_stop_all()
            else:
                print("错误: 请指定停止类型")
                return 1
        
        elif command == 'restart':
            restart_type = args.get('restart_type')
            
            if restart_type == 'dashboard':
                return self.handle_restart_dashboard()
            elif restart_type == 'agent':
                return self.handle_restart_agent()
            elif restart_type == 'all':
                return self.handle_restart_all()
            else:
                print("错误: 请指定重启类型")
                return 1
        
        elif command == 'status':
            status_type = args.get('status_type')
            
            if status_type == 'dashboard':
                return self.handle_status_dashboard()
            elif status_type == 'agent':
                return self.handle_status_agent()
            elif status_type == 'all':
                return self.handle_status_all()
            else:
                # 默认显示所有状态
                return self.handle_status_all()
        
        elif command == 'backup':
            return self.handle_backup(args)
        
        elif command == 'update':
            update_type = args.get('update_type')
            
            if update_type == 'dashboard':
                return self.handle_update_dashboard()
            elif update_type == 'agent':
                return self.handle_update_agent()
            elif update_type == 'all':
                return self.handle_update_all()
            else:
                print("错误: 请指定更新类型")
                return 1
        
        elif command == 'logs':
            logs_type = args.get('logs_type')
            
            if logs_type == 'dashboard':
                return self.handle_logs_dashboard(args)
            elif logs_type == 'agent':
                return self.handle_logs_agent(args)
            elif logs_type == 'system':
                return self.handle_logs_system(args)
            else:
                print("错误: 请指定日志类型")
                return 1
        
        else:
            print("错误: 未知命令")
            return 1
