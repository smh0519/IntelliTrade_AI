import requests
import time
import logging
from functools import wraps

# 로거 설정 (config/settings.py에서 LOG_LEVEL과 LOG_FILE_PATH를 가져와 설정할 수 있도록 추후 main.py에서 초기화)
# 현재는 기본 설정으로 시작합니다.
logger = logging.getLogger(__name__)

def handle_api_errors(max_retries=3, initial_delay=1.0, backoff_factor=2):
    """
    API 호출 시 발생할 수 있는 오류를 처리하고 재시도하는 데코레이터.
    HTTP 429 (Too Many Requests) 및 5xx 서버 오류에 대해 재시도를 수행합니다.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            while retries < max_retries:
                try:
                    response = func(*args, **kwargs)
                    response.raise_for_status()  # 200 OK가 아니면 HTTPError 발생
                    return response
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code
                    if status_code == 429: # Too Many Requests
                        logger.warning(f"API Rate Limit Exceeded (429). Retrying in {delay:.2f} seconds... (Attempt {retries + 1}/{max_retries})")
                        time.sleep(delay)
                        delay *= backoff_factor
                        retries += 1
                    elif 500 <= status_code < 600: # Server Error
                        logger.error(f"Server Error {status_code}. Retrying in {delay:.2f} seconds... (Attempt {retries + 1}/{max_retries})")
                        time.sleep(delay)
                        delay *= backoff_factor
                        retries += 1
                    else:
                        logger.error(f"HTTP Error {status_code} for {func.__name__}: {e}")
                        raise # 다른 HTTP 에러는 즉시 발생
                except requests.exceptions.ConnectionError as e:
                    logger.error(f"Connection Error for {func.__name__}: {e}. Retrying in {delay:.2f} seconds... (Attempt {retries + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= backoff_factor
                    retries += 1
                except requests.exceptions.Timeout as e:
                    logger.error(f"Timeout Error for {func.__name__}: {e}. Retrying in {delay:.2f} seconds... (Attempt {retries + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= backoff_factor
                    retries += 1
                except requests.exceptions.RequestException as e:
                    logger.error(f"An unexpected Request Error occurred for {func.__name__}: {e}")
                    raise # 그 외 requests 관련 에러는 즉시 발생
                except Exception as e:
                    logger.error(f"An unexpected error occurred in {func.__name__}: {e}")
                    raise # 예측 못한 다른 에러는 즉시 발생
            
            logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}.")
            raise requests.exceptions.RequestException(f"Failed to complete {func.__name__} after {max_retries} retries.")
        return wrapper
    return decorator

@handle_api_errors()
def get_request(url, headers=None, params=None, timeout=10):
    """
    GET 요청을 보내고 응답을 반환합니다.
    에러 처리 및 재시도 로직이 적용됩니다.
    """
    logger.debug(f"GET Request to: {url} with params: {params}")
    return requests.get(url, headers=headers, params=params, timeout=timeout)

@handle_api_errors()
def post_request(url, headers=None, data=None, json=None, timeout=10):
    """
    POST 요청을 보내고 응답을 반환합니다.
    에러 처리 및 재시도 로직이 적용됩니다.
    """
    logger.debug(f"POST Request to: {url} with data: {data}, json: {json}")
    return requests.post(url, headers=headers, data=data, json=json, timeout=timeout)

# 필요하다면 put, delete 등 다른 HTTP 메서드에 대한 래퍼 함수도 추가할 수 있습니다.
