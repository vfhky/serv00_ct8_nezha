import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from config.template_manager import TemplateManager
from utils.logger import get_logger

logger = get_logger()

def initialize_configs(base_dir: str) -> None:
    """
    初始化配置文件
    
    Args:
        base_dir: 基础目录
    """
    templates_dir = os.path.join(base_dir, 'config', 'templates')
    config_dir = os.path.join(base_dir, 'config')
    
    # 确保目录存在
    os.makedirs(templates_dir, exist_ok=True)
    
    template_manager = TemplateManager(templates_dir, config_dir)
    
    # 初始化所有模板
    templates = template_manager.list_templates()
    if not templates:
        logger.warning("没有找到可用的模板文件")
        return
    
    for template_name in templates:
        config_path = template_manager.get_config_path(template_name)
        if not os.path.exists(config_path):
            logger.info(f"创建配置文件: {config_path}")
            template_manager.create_config_from_template(template_name)
        else:
            logger.info(f"配置文件已存在: {config_path}")

def migrate_legacy_templates(base_dir: str) -> None:
    """
    迁移旧的模板文件到新的模板目录
    
    Args:
        base_dir: 基础目录
    """
    config_dir = os.path.join(base_dir, 'config')
    templates_dir = os.path.join(config_dir, 'templates')
    
    # 确保模板目录存在
    os.makedirs(templates_dir, exist_ok=True)
    
    # 模板文件映射
    template_map = {
        'sys.eg': 'sys.template',
        'host.eg': 'host.template',
        'monitor.eg': 'monitor.template',
        'heartbeat.eg': 'heartbeat.template'
    }
    
    # 迁移模板文件
    for old_name, new_name in template_map.items():
        old_path = os.path.join(config_dir, old_name)
        new_path = os.path.join(templates_dir, new_name)
        
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                with open(old_path, 'r') as f:
                    content = f.read()
                
                with open(new_path, 'w') as f:
                    f.write(content)
                
                logger.info(f"已迁移模板文件: {old_path} -> {new_path}")
            except Exception as e:
                logger.error(f"迁移模板文件失败: {old_path} -> {new_path}, 错误: {str(e)}")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    migrate_legacy_templates(base_dir)
    initialize_configs(base_dir)
