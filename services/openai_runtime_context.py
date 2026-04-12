from typing import Any, Dict, Optional

from config.settings import OPENAI_API_KEY, OPENAI_DEFAULT_MODEL
from database import db_manager
from .openai_client import OpenAIAPIError

DEFAULT_OPENAI_MODEL = OPENAI_DEFAULT_MODEL


async def load_runtime_context(user_id: int, logger: Optional[Any] = None) -> Dict[str, Any]:
    api_key = await db_manager.get_user_openai_api_key(user_id) or OPENAI_API_KEY
    if not api_key:
        raise OpenAIAPIError("OpenAI API key not found.", details={"error": {"message": "API_KEY_NOT_FOUND"}})

    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    if not active_dialog_id:
        if logger is not None:
            logger.error(f"У пользователя {user_id} нет активного диалога для OpenAI генерации ответа.")
        raise OpenAIAPIError("Не найден активный диалог. Пожалуйста, перезапустите бота командой /start.", details={})

    model_name = await db_manager.get_user_openai_model(user_id) or DEFAULT_OPENAI_MODEL
    history = await db_manager.get_conversation_history(active_dialog_id, limit=20)

    return {
        'api_key': api_key,
        'active_dialog_id': active_dialog_id,
        'model_name': model_name,
        'history': history,
    }
