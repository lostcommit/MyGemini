from typing import Any, Dict, List

from database import db_manager


def update_dialog_history_cache(
    history: List[Dict[str, Any]],
    user_parts: List[Dict[str, Any]],
    response_text: str,
    *,
    stateless: bool,
) -> None:
    """Append the latest user/model turns to in-memory history when context is stateful."""
    if stateless:
        return

    history.append({"role": "user", "parts": user_parts})
    history.append({"role": "model", "parts": [{"text": response_text}]})


async def persist_conversation_turn(
    *,
    user_id: int,
    dialog_id: int,
    user_message_for_db: str,
    response_text: str,
    usage: Dict[str, int],
) -> None:
    """Persist user and bot turns, including token usage for the bot response."""
    await db_manager.store_message(user_id, dialog_id, 'user', user_message_for_db)
    await db_manager.store_message(
        user_id=user_id,
        dialog_id=dialog_id,
        role='bot',
        message_text=response_text,
        prompt_tokens=usage['prompt_tokens'],
        completion_tokens=usage['completion_tokens'],
        total_tokens=usage['total_tokens'],
    )
