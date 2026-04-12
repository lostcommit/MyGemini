import asyncio
import random
from typing import Any, Dict, Optional

import aiohttp

from logger_config import get_logger


openai_logger = get_logger('openai_api')

OPENAI_API_BASE_URL = "https://api.openai.com/v1"
_http_session: Optional[aiohttp.ClientSession] = None


class OpenAIAPIError(Exception):
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {}
        self.error_key = self._resolve_error_key(message, self.details)

    @staticmethod
    def _resolve_error_key(message: str, details: Optional[Dict]) -> str:
        error_message = (details or {}).get("error", {}).get("message", "") or ""
        combined = f"{message} {error_message}".lower()

        if any(token in combined for token in ["invalid api key", "incorrect api key", "api key", "authentication", "unauthorized"]):
            return "openai_error_api_key_invalid"
        if any(token in combined for token in ["permission", "forbidden"]):
            return "openai_error_permission_denied"
        if any(token in combined for token in ["rate limit", "quota", "insufficient_quota", "too many requests"]):
            return "openai_error_quota_exceeded"
        if "timeout" in combined:
            return "openai_error_timeout"
        if any(token in combined for token in ["service_unavailable", "server error", "overloaded", "temporarily unavailable", "bad gateway"]):
            return "openai_error_unavailable"
        if any(token in combined for token in ["invalid_request_error", "invalid request", "invalid image", "unsupported image"]):
            return "openai_error_invalid_argument"
        if "api_key_not_found" in combined:
            return "api_key_needed_for_feature"
        return "openai_error_unknown"


async def init_http_session():
    global _http_session
    if _http_session is None or _http_session.closed:
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=60)
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10, ttl_dns_cache=300)
        _http_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        openai_logger.info("Общая HTTP-сессия OpenAI API инициализирована.", extra={'user_id': 'System'})


async def close_http_session():
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()
        openai_logger.info("Общая HTTP-сессия OpenAI API закрыта.", extra={'user_id': 'System'})
    _http_session = None


async def get_http_session() -> aiohttp.ClientSession:
    if _http_session is None or _http_session.closed:
        await init_http_session()
    return _http_session


async def make_openai_request_async(
    api_key: str,
    url: str,
    payload: Optional[Dict] = None,
    method: str = 'POST',
) -> Dict[str, Any]:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }

    max_retries = 3
    base_retry_delay = 2

    for attempt in range(max_retries):
        try:
            session = await get_http_session()
            request_args = {'headers': headers}
            if payload is not None:
                request_args['json'] = payload

            async with session.request(method, url, **request_args) as response:
                response_json = await response.json()
                if response.status != 200:
                    error_details = response_json.get('error', {})
                    error_message = error_details.get('message', 'Unknown OpenAI API error')

                    if response.status >= 500 or response.status == 429:
                        if attempt < max_retries - 1:
                            retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                            await asyncio.sleep(retry_delay)
                            continue

                    raise OpenAIAPIError(error_message, details=response_json)

                return response_json

        except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
            if attempt < max_retries - 1:
                retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                await asyncio.sleep(retry_delay)
                continue
            raise OpenAIAPIError("OpenAI server timeout", details={"error": {"message": "service_timeout"}})
        except aiohttp.ClientError:
            if attempt < max_retries - 1:
                retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                await asyncio.sleep(retry_delay)
                continue
            raise OpenAIAPIError("Network error", details={"error": {"message": "service_unavailable"}})
        except OpenAIAPIError:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                retry_delay = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 0.5)
                await asyncio.sleep(retry_delay)
                continue
            raise OpenAIAPIError(f"Unexpected error: {e}", details={"error": {"message": "unknown_error"}})

    raise OpenAIAPIError("Failed to get OpenAI response after retries", details={"error": {"message": "service_unavailable"}})
