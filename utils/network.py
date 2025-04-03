import socket
import requests
from typing import Optional, Tuple, Dict, Any
from utils.logger import get_logger

logger = get_logger()

def check_dns_resolution(domain: str) -> Tuple[bool, Optional[str]]:
    """
    检查域名DNS解析
    
    Args:
        domain: 要检查的域名
        
    Returns:
        Tuple[bool, Optional[str]]: 解析是否成功和解析结果
    """
    try:
        host = socket.gethostbyname(domain)
        logger.info(f"域名 {domain} 解析成功，IP地址为: {host}")
        return True, host
    except socket.gaierror as e:
        logger.error(f"域名 {domain} 解析失败: {str(e)}")
        return False, None

def get_url_domain(url: str) -> Optional[str]:
    """
    从URL中提取域名
    
    Args:
        url: URL地址
        
    Returns:
        Optional[str]: 提取的域名，如果提取失败则返回None
    """
    try:
        if url.startswith('http'):
            parts = url.split('/')
            if len(parts) >= 3:
                return parts[2]
        return None
    except Exception as e:
        logger.error(f"从URL提取域名失败: {url}, 错误: {str(e)}")
        return None

def http_get_request(url: str, timeout: int = 5, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    发送HTTP GET请求
    
    Args:
        url: 请求的URL
        timeout: 超时时间（秒）
        headers: 请求头
        
    Returns:
        Tuple[bool, Optional[int], Optional[str]]: 请求是否成功、状态码和响应内容
    """
    try:
        response = requests.get(url, timeout=timeout, headers=headers)
        return True, response.status_code, response.text
    except requests.RequestException as e:
        logger.error(f"HTTP GET请求失败: {url}, 错误: {str(e)}")
        return False, None, str(e)

def http_post_request(url: str, data: Any = None, json: Any = None, timeout: int = 5, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    发送HTTP POST请求
    
    Args:
        url: 请求的URL
        data: 表单数据
        json: JSON数据
        timeout: 超时时间（秒）
        headers: 请求头
        
    Returns:
        Tuple[bool, Optional[int], Optional[str]]: 请求是否成功、状态码和响应内容
    """
    try:
        response = requests.post(url, data=data, json=json, timeout=timeout, headers=headers)
        return True, response.status_code, response.text
    except requests.RequestException as e:
        logger.error(f"HTTP POST请求失败: {url}, 错误: {str(e)}")
        return False, None, str(e)

def is_port_open(host: str, port: int, timeout: int = 2) -> bool:
    """
    检查主机端口是否开放
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间（秒）
        
    Returns:
        bool: 端口是否开放
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info(f"端口开放: {host}:{port}")
            return True
        else:
            logger.info(f"端口未开放: {host}:{port}")
            return False
    except Exception as e:
        logger.error(f"检查端口开放状态失败: {host}:{port}, 错误: {str(e)}")
        return False
