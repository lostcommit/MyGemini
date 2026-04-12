import datetime
from typing import Any, Dict, List, Optional

from logger_config import get_logger
from .core import _execute_query


db_logger = get_logger('database', user_id='System')


async def create_dialog(user_id: int, name: str, set_active: bool = False) -> Optional[int]:
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    query = "INSERT INTO dialogs (user_id, name, created_at) VALUES (?, ?, ?)"
    new_dialog_id = await _execute_query(query, (user_id, name, now_str), is_write_operation=True)
    if new_dialog_id:
        if set_active:
            await set_active_dialog(user_id, new_dialog_id)
        db_logger.info(f"Для пользователя {user_id} создан новый диалог '{name}' (ID: {new_dialog_id}).")
        return int(new_dialog_id)
    return None


async def start_fresh_dialog(user_id: int, name: str) -> Optional[int]:
    new_dialog_id = await create_dialog(user_id, name, set_active=True)
    if new_dialog_id:
        db_logger.info(f"Для пользователя {user_id} начат новый чистый диалог (ID: {new_dialog_id}).")
    return new_dialog_id


async def get_user_dialogs(user_id: int) -> List[Dict[str, Any]]:
    query = "SELECT d.dialog_id, d.name, u.active_dialog_id FROM dialogs d JOIN users u ON d.user_id = u.user_id WHERE d.user_id = ? ORDER BY d.created_at DESC"
    rows = await _execute_query(query, (user_id,), fetch_all=True)
    return [dict(row) for row in rows] if rows else []


async def set_active_dialog(user_id: int, dialog_id: int) -> bool:
    query = """
        UPDATE users
        SET active_dialog_id = ?
        WHERE user_id = ?
          AND EXISTS (
              SELECT 1 FROM dialogs WHERE dialog_id = ? AND user_id = ?
          )
    """
    rows_affected = await _execute_query(query, (dialog_id, user_id, dialog_id, user_id), is_write_operation=True)
    if rows_affected:
        db_logger.info(f"Для пользователя {user_id} установлен активный диалог ID: {dialog_id}.")
        return True
    db_logger.warning(f"Не удалось установить dialog_id={dialog_id} активным для пользователя {user_id}: диалог не найден или не принадлежит пользователю.")
    return False


async def rename_dialog(user_id: int, dialog_id: int, new_name: str) -> bool:
    query = "UPDATE dialogs SET name = ? WHERE dialog_id = ? AND user_id = ?"
    rows_affected = await _execute_query(query, (new_name, dialog_id, user_id), is_write_operation=True)
    if rows_affected:
        db_logger.info(f"Диалог ID {dialog_id} пользователя {user_id} переименован в '{new_name}'.")
        return True
    db_logger.warning(f"Не удалось переименовать dialog_id={dialog_id} для пользователя {user_id}: диалог не найден или не принадлежит пользователю.")
    return False


async def delete_dialog(user_id: int, dialog_id_to_delete: int) -> Optional[str]:
    other_dialogs = await _execute_query(
        "SELECT dialog_id FROM dialogs WHERE user_id = ? AND dialog_id != ? ORDER BY created_at DESC",
        (user_id, dialog_id_to_delete),
        fetch_all=True,
    )
    if not other_dialogs:
        db_logger.warning(f"Попытка удалить последний диалог {dialog_id_to_delete} для пользователя {user_id}. Операция отменена.")
        return None

    active_dialog_id = await get_active_dialog_id(user_id)
    if active_dialog_id == dialog_id_to_delete:
        new_active_dialog_id = other_dialogs[0]['dialog_id']
        await set_active_dialog(user_id, new_active_dialog_id)

    dialog_info = await _execute_query(
        "SELECT name FROM dialogs WHERE dialog_id = ? AND user_id = ?",
        (dialog_id_to_delete, user_id),
        fetch_one=True,
    )
    if not dialog_info:
        return None

    delete_query = "DELETE FROM dialogs WHERE dialog_id = ? AND user_id = ?"
    rows_affected = await _execute_query(delete_query, (dialog_id_to_delete, user_id), is_write_operation=True)
    if rows_affected:
        db_logger.info(f"Диалог ID {dialog_id_to_delete} удален для пользователя {user_id}.")
        return dialog_info['name']
    return None


async def get_active_dialog_id(user_id: int) -> Optional[int]:
    query = "SELECT active_dialog_id FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['active_dialog_id'] if result else None


async def get_user_context_info(user_id: int) -> Optional[Dict[str, Any]]:
    query = """
        SELECT
            d.name as dialog_name,
            u.gemini_model,
            u.active_persona
        FROM users u
        LEFT JOIN dialogs d ON u.active_dialog_id = d.dialog_id
        WHERE u.user_id = ?
    """
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return dict(result) if result else None
