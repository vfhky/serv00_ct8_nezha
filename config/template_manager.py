# config/template_manager.py
import os
import shutil
from typing import Dict, List, Optional
from utils.logger import get_logger

logger = get_logger()

class TemplateManager:
    """
    模板管理器，负责管理配置模板
    """
    
    def __init__(self, templates_dir: str, config_dir: str):
        """
        初始化模板管理器
        
        Args:
            templates_dir: 模板目录
            config_dir: 配置目录
        """
        self.templates_dir = templates_dir
        self.config_dir = config_dir
    
    def get_template_path(self, template_name: str) -> str:
        """
        获取模板文件路径
        
        Args:
            template_name: 模板名称
            
        Returns:
            str: 模板文件路径
        """
        return os.path.join(self.templates_dir, f"{template_name}.template")
    
    def get_config_path(self, config_name: str) -> str:
        """
        获取配置文件路径
        
        Args:
            config_name: 配置名称
            
        Returns:
            str: 配置文件路径
        """
        return os.path.join(self.config_dir, f"{config_name}.conf")
    
    def list_templates(self) -> List[str]:
        """
        列出所有可用的模板
        
        Returns:
            List[str]: 模板名称列表
        """
        templates = []
        if os.path.exists(self.templates_dir):
            for file in os.listdir(self.templates_dir):
                if file.endswith('.template'):
                    templates.append(file[:-9])  # 去掉 .template 后缀
        return templates
    
    def create_config_from_template(self, template_name: str, config_name: Optional[str] = None) -> Optional[str]:
        """
        从模板创建配置文件
        
        Args:
            template_name: 模板名称
            config_name: 配置名称，如果不指定则使用模板名称
            
        Returns:
            Optional[str]: 创建的配置文件路径，如果创建失败则返回None
        """
        if config_name is None:
            config_name = template_name
        
        template_path = self.get_template_path(template_name)
        config_path = self.get_config_path(config_name)
        
        if not os.path.exists(template_path):
            logger.error(f"模板文件不存在: {template_path}")
            return None
        
        # 如果配置文件已存在，创建备份
        if os.path.exists(config_path):
            backup_path = f"{config_path}.bak"
            shutil.copy2(config_path, backup_path)
            logger.info(f"已创建配置文件备份: {backup_path}")
        
        # 复制模板到配置文件
        try:
            shutil.copy2(template_path, config_path)
            logger.info(f"已从模板 {template_name} 创建配置文件: {config_path}")
            return config_path
        except Exception as e:
            logger.error(f"创建配置文件失败: {str(e)}")
            return None
    
    def update_config_from_template(self, template_name: str, config_name: Optional[str] = None, merge: bool = True) -> Optional[str]:
        """
        从模板更新配置文件，保留现有配置的值
        
        Args:
            template_name: 模板名称
            config_name: 配置名称，如果不指定则使用模板名称
            merge: 是否合并现有配置的值
            
        Returns:
            Optional[str]: 更新的配置文件路径，如果更新失败则返回None
        """
        if config_name is None:
            config_name = template_name
        
        template_path = self.get_template_path(template_name)
        config_path = self.get_config_path(config_name)
        
        if not os.path.exists(template_path):
            logger.error(f"模板文件不存在: {template_path}")
            return None
        
        if not os.path.exists(config_path):
            # 如果配置文件不存在，直接创建
            return self.create_config_from_template(template_name, config_name)
        
        if not merge:
            # 如果不需要合并，直接覆盖
            return self.create_config_from_template(template_name, config_name)
        
        # 读取现有配置的值
        existing_values = {}
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            existing_values[key.strip()] = value.strip()
                        except ValueError:
                            # 忽略格式不正确的行
                            pass
        except Exception as e:
            logger.error(f"读取配置文件失败: {str(e)}")
            return None
        
        # 创建备份
        backup_path = f"{config_path}.bak"
        shutil.copy2(config_path, backup_path)
        logger.info(f"已创建配置文件备份: {backup_path}")
        
        # 从模板更新配置文件，保留现有值
        try:
            with open(template_path, 'r') as template_f:
                template_lines = template_f.readlines()
            
            with open(config_path, 'w') as config_f:
                for line in template_lines:
                    line_stripped = line.strip()
                    if line_stripped and not line_stripped.startswith('#'):
                        try:
                            key, _ = line_stripped.split('=', 1)
                            key = key.strip()
                            if key in existing_values:
                                # 使用现有值
                                config_f.write(f"{key}={existing_values[key]}\n")
                                continue
                        except ValueError:
                            # 忽略格式不正确的行
                            pass
                    
                    # 使用模板值
                    config_f.write(line)
            
            logger.info(f"已从模板 {template_name} 更新配置文件: {config_path}")
            return config_path
        except Exception as e:
            logger.error(f"更新配置文件失败: {str(e)}")
            return None