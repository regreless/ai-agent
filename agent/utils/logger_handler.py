import os
import logging
import datetime

from agent.utils.path_tool import get_abs_path

LOG_ROOT = get_abs_path('logs')

os.makedirs(LOG_ROOT, exist_ok=True)

DEFAULT_LOG_FORMAT = '%(asctime)s %(name)-12s %(levelname)-8s %(filename)s:%(lineno)d - %(message)s'


def get_logger(
        name: str = "agent",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        log_file=None,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加Handler
    if logger.handlers:
        return logger

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    # 控制台Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # 文件Handler
    if not log_file:
        log_file = os.path.join(LOG_ROOT, f"{name}_{datetime.datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = get_logger()
