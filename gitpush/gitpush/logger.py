#!/usr/bin/env python3
import logging
import os
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gitpush.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 创建全局日志对象
logger = logging.getLogger('gitpush')


def log(message, level=logging.INFO):
    """最小日志能力函数
    
    Args:
        message (str): 日志消息
        level (int): 日志级别，默认 INFO
    """
    logger.log(level, message)
