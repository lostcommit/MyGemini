from typing import Optional

from database import db_manager
from .gemini_history_cache import reset_dialog_chat


def _default_dialog_name(lang_code: str, *, fresh: bool = False) -> str:
    if fresh:
        return "Новый диалог" if lang_code == 'ru' else "Fresh dialog"
    return "Основной диалог" if lang_code == 'ru' else "General Chat"


async def reset_active_dialog_cache(user_id: int) -> Optional[int]:
    """Reset the Gemini cache for the current active dialog, if any."""
    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    if active_dialog_id:
        reset_dialog_chat(active_dialog_id)
    return active_dialog_id


async def start_fresh_dialog(user_id: int, lang_code: str) -> Optional[int]:
    """Create and activate a new fresh dialog for the user."""
    new_dialog_id = await db_manager.start_fresh_dialog(user_id, _default_dialog_name(lang_code, fresh=True))
    if new_dialog_id:
        reset_dialog_chat(new_dialog_id)
    return new_dialog_id


async def create_dialog(user_id: int, dialog_name: str) -> Optional[int]:
    """Create a user dialog and reset the newly active dialog cache."""
    dialog_id = await db_manager.create_dialog(user_id, dialog_name, set_active=True)
    if dialog_id:
        reset_dialog_chat(dialog_id)
    return dialog_id


async def switch_dialog(user_id: int, dialog_id: int) -> bool:
    """Switch active dialog and clear the new active dialog cache."""
    switched = await db_manager.set_active_dialog(user_id, dialog_id)
    if switched:
        reset_dialog_chat(dialog_id)
    return switched


async def rename_dialog(user_id: int, dialog_id: int, new_name: str) -> bool:
    """Rename a dialog owned by the user."""
    return await db_manager.rename_dialog(user_id, dialog_id, new_name)


async def delete_dialog(user_id: int, dialog_id: int, lang_code: str) -> tuple[Optional[str], bool]:
    """Delete a dialog and ensure the user still has an active dialog.

    Returns: (deleted_dialog_name, created_fallback_dialog)
    """
    deleted_dialog_name = await db_manager.delete_dialog(user_id, dialog_id)
    if not deleted_dialog_name:
        return None, False

    remaining_dialogs = await db_manager.get_user_dialogs(user_id)
    if remaining_dialogs:
        active_dialog_id = await db_manager.get_active_dialog_id(user_id)
        if active_dialog_id:
            reset_dialog_chat(active_dialog_id)
        return deleted_dialog_name, False

    new_dialog_id = await db_manager.create_dialog(user_id, _default_dialog_name(lang_code), set_active=True)
    if new_dialog_id:
        reset_dialog_chat(new_dialog_id)
    return deleted_dialog_name, True
