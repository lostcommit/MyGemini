from typing import Optional

from logger_config import get_logger
from .core import _execute_query


db_logger = get_logger('database', user_id='System')


async def set_app_setting(key: str, value: str):
    query = "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value"
    await _execute_query(query, (key, value), is_write_operation=True)
    db_logger.info(f"Глобальная настройка '{key}' установлена в значение '{value}'.")


async def get_app_setting(key: str) -> Optional[str]:
    query = "SELECT value FROM app_settings WHERE key = ?"
    result = await _execute_query(query, (key,), fetch_one=True)
    return result['value'] if result else None
