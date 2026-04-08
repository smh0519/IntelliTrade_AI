# utils/logger.py
import logging
import os
from config import LOG_LEVEL, LOG_FILE_PATH

def setup_logger():
    """
    프로그램 전체에서 사용할 로거를 설정합니다.
    콘솔 출력과 파일 저장을 동시에 지원합니다.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)

    # 핸들러가 이미 설정되어 있지 않은 경우에만 설정
    if not logger.handlers:
        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)

        # 파일 핸들러 설정
        # 로그 파일 디렉토리가 없으면 생성
        log_dir = os.path.dirname(LOG_FILE_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

    return logger

# 프로그램 전역에서 사용할 로거 인스턴스
logger = setup_logger()
