import asyncio
import random
from typing import Any, Dict, Optional

import aiohttp

from logger_config import get_logger
from .error_parser import get_user_friendly_error_key


gemini_logger = get_logger('gemini_api')

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_http_session: Optional[aiohttp.ClientSession] = None


class GeminiAPIError(Exception):
    """Кастомное исключение для ошибок Gemini API."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {}
        self.error_key = get_user_friendly_error_key(self.details)


async def init_http_session():
    """Инициализирует общую HTTP-сессию для Gemini API."""
    global _http_session
    if _http_session is None or _http_session.closed:
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=60)
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10, ttl_dns_cache=300)
        _http_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        gemini_logger.info("Общая HTTP-сессия Gemini API инициализирована.", extra={'user_id': 'System'})


async def close_http_session():
    """Закрывает общую HTTP-сессию для Gemini API."""
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()
        gemini_logger.info("Общая HTTP-сессия Gemini API закрыта.", extra={'user_id': 'System'})
    _http_session = None


async def get_http_session() -> aiohttp.ClientSession:
    if _http_session is None or _http_session.closed:
        await init_http_session()
    return _http_session


async def make_gemini_request_async(
    api_key: str,
    url: str,
    payload: Optional[Dict] = None,
    method: str = 'POST',
) -> Dict[str, Any]:
    """
    Выполняет универсальный асинхронный HTTP-запрос к Gemini API.
    В случае ошибки выбрасывает GeminiAPIError.
    Реализует механизм повторных попыток для временных ошибок.
    """
    headers = {'Content-Type': 'application/json'}
    params = {'key': api_key}

    max_retries = 3
    base_retry_delay = 2

    for attempt in range(max_retries):
        try:
            session = await get_http_session()
            request_args = {'params': params, 'headers': headers}
            if payload:
                request_args['json'] = payload

            async with session.request(method, url, **request_args) as response:
                response_json = await response.json()
                if response.status != 200:
                    error_details = response_json.get('error', {})
                    error_message = error_details.get('message', 'Неизвестная ошибка API')

                    if response.status >= 500 or response.status == 429:
                        if attempt < max_retries - 1:
                            retry_after_header = response.headers.get('Retry-After')
                            if retry_after_header and retry_after_header.isdigit():
                                retry_delay = float(retry_after_header)
                            else:
                                retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                            gemini_logger.warning(
                                f"Попытка {attempt + 1}/{max_retries}: "
                                f"Получена временная ошибка (HTTP {response.status}). "
                                f"Повтор через {retry_delay} сек. Ошибка: {error_message}",
                                extra={'user_id': 'System'}
                            )
                            await asyncio.sleep(retry_delay)
                            continue

                    gemini_logger.error(f"Ошибка API Gemini (HTTP {response.status}): {response_json}", extra={'user_id': 'System'})
                    raise GeminiAPIError(error_message, details=error_details)

                return response_json

        except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
            gemini_logger.error(f"Тайм-аут при запросе к Gemini API после {attempt + 1} попыток.", extra={'user_id': 'System'})
            if attempt < max_retries - 1:
                retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                await asyncio.sleep(retry_delay)
                continue
            raise GeminiAPIError("Сервер не ответил вовремя.", details={"error": {"message": "service_timeout"}})
        except aiohttp.ClientError as e:
            gemini_logger.exception(f"Сетевая ошибка при запросе к Gemini API: {e}", extra={'user_id': 'System'})
            if attempt < max_retries - 1:
                retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                await asyncio.sleep(retry_delay)
                continue
            raise GeminiAPIError("Сетевая ошибка при подключении к сервису.", details={"error": {"message": "service_unavailable"}})
        except GeminiAPIError:
            raise
        except Exception as e:
            gemini_logger.exception(f"Неожиданная ошибка при выполнении запроса к Gemini API: {e}", extra={'user_id': 'System'})
            if attempt < max_retries - 1:
                retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                await asyncio.sleep(retry_delay)
                continue
            raise GeminiAPIError(f"Неожиданная ошибка: {e}", details={"error": {"message": "unknown_error"}})

    raise GeminiAPIError("Не удалось получить ответ от API после нескольких попыток.", details={"error": {"message": "service_unavailable"}})
