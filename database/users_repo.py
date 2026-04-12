import datetime
from typing import Any, Dict, Optional

from config.settings import DEFAULT_MODEL_ID
from logger_config import get_logger
from utils import crypto_helpers
from .core import _execute_query, db_logger, get_new_user_notifier
from .dialogs_repo import create_dialog


async def add_or_update_user(user_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]) -> bool:
    user_data = await _execute_query("SELECT user_id, active_dialog_id FROM users WHERE user_id = ?", (user_id,), fetch_one=True)

    if not user_data:
        db_logger.info(f"Добавляем нового пользователя {user_id} (@{username}).")
        today_date_str = datetime.date.today().strftime('%Y-%m-%d')
        query_insert_user = """
            INSERT INTO users (user_id, username, first_name, last_name, first_interaction_date, gemini_model)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (user_id, username, first_name, last_name, today_date_str, DEFAULT_MODEL_ID)
        await _execute_query(query_insert_user, params, is_write_operation=True)
        notifier = get_new_user_notifier()
        if notifier:
            await notifier(user_id, username, first_name, last_name)
        await create_dialog(user_id, "Основной диалог", set_active=True)
        return True

    query_update_user = """
        UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE user_id = ?
    """
    params = (username, first_name, last_name, user_id)
    await _execute_query(query_update_user, params, is_write_operation=True)

    if not user_data['active_dialog_id']:
        db_logger.warning(f"У существующего пользователя {user_id} нет активного диалога. Создаем новый.")
        await create_dialog(user_id, "Основной диалог", set_active=True)
    return False


async def set_user_bot_style(user_id: int, style: str):
    user_info = await _execute_query("SELECT username, first_name, last_name FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if not user_info:
        db_logger.warning(f"Невозможно установить bot_style: пользователь {user_id} не найден.")
        return False
    query = "UPDATE users SET bot_style = ? WHERE user_id = ?"
    await _execute_query(query, (style, user_id), is_write_operation=True)
    return True


async def get_user_bot_style(user_id: int) -> str:
    result = await _execute_query("SELECT bot_style FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return result['bot_style'] if result else 'default'


async def set_user_api_key(user_id: int, api_key: Optional[str]):
    user_info = await _execute_query("SELECT username, first_name, last_name FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if not user_info:
        db_logger.warning(f"Невозможно изменить API-ключ: пользователь {user_id} не найден.")
        return False
    encrypted_key = crypto_helpers.encrypt_data(api_key) if api_key else None
    await _execute_query("UPDATE users SET api_key = ? WHERE user_id = ?", (encrypted_key, user_id), is_write_operation=True)
    db_logger.info(f"API-ключ для пользователя {user_id} {'установлен' if api_key else 'сброшен'}.")
    return True


async def get_user_api_key(user_id: int) -> Optional[str]:
    result = await _execute_query("SELECT api_key FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if result and result['api_key']:
        encrypted_key = result['api_key']
        try:
            return crypto_helpers.decrypt_data(encrypted_key)
        except Exception as e:
            db_logger.exception(f"Ошибка при дешифровании API-ключа для {user_id}: {e}", extra={'user_id': str(user_id)})
            return None
    return None


async def set_user_language(user_id: int, lang_code: str):
    user_info = await _execute_query("SELECT username, first_name, last_name FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if not user_info:
        db_logger.warning(f"Невозможно установить язык: пользователь {user_id} не найден.")
        return False
    await _execute_query("UPDATE users SET language_code = ? WHERE user_id = ?", (lang_code, user_id), is_write_operation=True)
    return True


async def get_user_language(user_id: int) -> str:
    result = await _execute_query("SELECT language_code FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return result['language_code'] if result and result['language_code'] else 'ru'


async def set_user_gemini_model(user_id: int, model_name: str):
    user_info = await _execute_query("SELECT username, first_name, last_name FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if not user_info:
        db_logger.warning(f"Невозможно установить модель Gemini: пользователь {user_id} не найден.")
        return False
    await _execute_query("UPDATE users SET gemini_model = ? WHERE user_id = ?", (model_name, user_id), is_write_operation=True)
    return True


async def get_user_gemini_model(user_id: int) -> Optional[str]:
    result = await _execute_query("SELECT gemini_model FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return result['gemini_model'] if result and result['gemini_model'] else None


async def set_user_persona(user_id: int, persona_id: str):
    user_info = await _execute_query("SELECT username, first_name, last_name FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if not user_info:
        db_logger.warning(f"Невозможно установить персону: пользователь {user_id} не найден.")
        return False
    await _execute_query("UPDATE users SET active_persona = ? WHERE user_id = ?", (persona_id, user_id), is_write_operation=True)
    return True


async def get_user_persona(user_id: int) -> str:
    result = await _execute_query("SELECT active_persona FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return result['active_persona'] if result and result['active_persona'] else 'default'


async def get_first_interaction_date(user_id: int) -> Optional[str]:
    result = await _execute_query("SELECT first_interaction_date FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return result['first_interaction_date'] if result else None


async def is_user_blocked(user_id: int) -> bool:
    result = await _execute_query("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return result['is_blocked'] == 1 if result else False


async def block_user(user_id: int):
    await _execute_query("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,), is_write_operation=True)
    db_logger.info(f"Пользователь {user_id} заблокирован.")


async def unblock_user(user_id: int):
    await _execute_query("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,), is_write_operation=True)
    db_logger.info(f"Пользователь {user_id} разблокирован.")
