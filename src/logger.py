import logging
import os
from datetime import datetime

# 创建logs目录
os.makedirs('logs', exist_ok=True)

# 配置日志 - 设置为INFO级别
logging.basicConfig(
    level=logging.INFO,  # 设置为INFO级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/translation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

def get_logger(name):
    return logging.getLogger(name)
