# config/validator.py
import re
from typing import Dict, Any, List, Optional, Callable, Union

class ConfigValidator:
    """
    配置验证器，用于验证配置是否有效
    """
    
    @staticmethod
    def validate_required(config: Dict[str, Any], required_keys: List[str]) -> List[str]:
        """
        验证必需的配置键
        
        Args:
            config: 配置字典
            required_keys: 必需的键列表
            
        Returns:
            List[str]: 缺失的键列表
        """
        missing_keys = []
        for key in required_keys:
            if key not in config or not config[key]:
                missing_keys.append(key)
        return missing_keys
    
    @staticmethod
    def validate_format(config: Dict[str, Any], format_rules: Dict[str, Dict[str, Union[str, Callable]]]) -> Dict[str, str]:
        """
        验证配置值的格式
        
        Args:
            config: 配置字典
            format_rules: 格式规则字典，键为配置键，值为规则字典
                规则字典中的 'pattern' 键对应正则表达式或验证函数
                规则字典中的 'message' 键对应验证失败时的错误消息
            
        Returns:
            Dict[str, str]: 验证失败的键和对应的错误消息
        """
        invalid_formats = {}
        for key, rules in format_rules.items():
            if key not in config:
                continue
            
            value = config[key]
            pattern = rules.get('pattern')
            
            # 如果pattern是函数，则调用函数验证
            if callable(pattern):
                is_valid = pattern(value)
            # 否则按正则表达式验证
            elif isinstance(pattern, str) and isinstance(value, str):
                is_valid = bool(re.match(pattern, value))
            else:
                is_valid = False
            
            if not is_valid:
                invalid_formats[key] = rules.get('message', f"'{key}'的值格式无效")
        
        return invalid_formats
    
    @staticmethod
    def validate_dependencies(config: Dict[str, Any], dependencies: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        验证配置的依赖关系
        
        Args:
            config: 配置字典
            dependencies: 依赖关系字典，键为依赖的键，值为被依赖的键列表
            
        Returns:
            Dict[str, List[str]]: 验证失败的依赖关系，键为依赖的键，值为缺失的被依赖键列表
        """
        missing_dependencies = {}
        for key, depends_on in dependencies.items():
            if key in config and config[key]:
                missing = []
                for dep_key in depends_on:
                    if dep_key not in config or not config[dep_key]:
                        missing.append(dep_key)
                if missing:
                    missing_dependencies[key] = missing
        
        return missing_dependencies