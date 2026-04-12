from typing import Any, Awaitable, Callable, Dict, List, Optional

from config.settings import DEFAULT_MODEL_ID
from database import db_manager
from .gemini_client import GeminiAPIError
from .gemini_request_builder import is_stateless_model


HistoryLoader = Callable[[int], Awaitable[List[Dict[str, Any]]]]


async def load_runtime_context(
    user_id: int,
    *,
    history_loader: HistoryLoader,
    logger: Optional[Any] = None,
) -> Dict[str, Any]:
    """Load all preflight/runtime data needed before making a Gemini request."""
    api_key = await db_manager.get_user_api_key(user_id)
    if not api_key:
        raise GeminiAPIError("API-ключ пользователя не найден.", details={"error": {"message": "API_KEY_NOT_FOUND"}})

    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    if not active_dialog_id:
        if logger is not None:
            logger.error(f"У пользователя {user_id} нет активного диалога для генерации ответа.")
        raise GeminiAPIError("Не найден активный диалог. Пожалуйста, перезапустите бота командой /start.", details={})

    model_name = await db_manager.get_user_gemini_model(user_id) or DEFAULT_MODEL_ID
    stateless = is_stateless_model(model_name)

    history: List[Dict[str, Any]] = []
    if not stateless:
        history = await history_loader(active_dialog_id)

    return {
        'api_key': api_key,
        'active_dialog_id': active_dialog_id,
        'model_name': model_name,
        'stateless': stateless,
        'history': history,
    }
