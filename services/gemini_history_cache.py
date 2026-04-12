from typing import Any, Dict, List

from cachetools import LRUCache

from database import db_manager
from logger_config import get_logger


gemini_logger = get_logger('gemini_api')

# Кэш для хранения истории диалогов. Ограничен по размеру для предотвращения утечек памяти.
# maxsize=100 означает, что в памяти будет храниться история 100 последних используемых диалогов.
dialog_chats_cache: LRUCache = LRUCache(maxsize=100)


async def get_dialog_chat_history(dialog_id: int) -> List[Dict[str, Any]]:
    """Return or build cached Gemini chat history for a dialog."""
    if dialog_id not in dialog_chats_cache:
        gemini_logger.debug(f"Кэш истории для dialog_id: {dialog_id} не найден. Загрузка из БД.")
        history_from_db = await db_manager.get_conversation_history(dialog_id, limit=20)
        gemini_history = []
        for item in history_from_db:
            role = 'user' if item.get('role') == 'user' else 'model'
            gemini_history.append({"role": role, "parts": [{"text": item.get('message_text', '')}]})
        dialog_chats_cache[dialog_id] = gemini_history
        gemini_logger.info(f"История для dialog_id: {dialog_id} загружена в кэш ({len(gemini_history)} сообщений).")
    return dialog_chats_cache[dialog_id]


def reset_dialog_chat(dialog_id: int):
    """Reset cached history for a dialog."""
    if dialog_id in dialog_chats_cache:
        del dialog_chats_cache[dialog_id]
        gemini_logger.info(f"История чата в кэше для dialog_id: {dialog_id} сброшена.")
