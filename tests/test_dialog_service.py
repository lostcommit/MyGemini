import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_switch_dialog_resets_new_active_dialog_cache(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.dialog_service", None)
    sys.modules.pop("services.gemini_history_cache", None)
    dialog_service = importlib.import_module("services.dialog_service")
    dialog_service = importlib.reload(dialog_service)
    gemini_history_cache = importlib.import_module("services.gemini_history_cache")
    gemini_history_cache = importlib.reload(gemini_history_cache)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    original_dialog_id = await db_manager.get_active_dialog_id(1)
    new_dialog_id = await db_manager.create_dialog(1, "Second dialog", set_active=False)
    assert original_dialog_id is not None
    assert new_dialog_id is not None

    gemini_history_cache.dialog_chats_cache[int(new_dialog_id)] = [{"role": "model", "parts": [{"text": "stale"}]}]

    switched = await dialog_service.switch_dialog(1, int(new_dialog_id))

    assert switched is True
    assert int(new_dialog_id) not in gemini_history_cache.dialog_chats_cache


@pytest.mark.asyncio
async def test_create_dialog_resets_created_dialog_cache(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.dialog_service", None)
    sys.modules.pop("services.gemini_history_cache", None)
    dialog_service = importlib.import_module("services.dialog_service")
    dialog_service = importlib.reload(dialog_service)
    gemini_history_cache = importlib.import_module("services.gemini_history_cache")
    gemini_history_cache = importlib.reload(gemini_history_cache)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    created_dialog_id = await dialog_service.create_dialog(1, "Fresh")
    assert created_dialog_id is not None

    gemini_history_cache.dialog_chats_cache[int(created_dialog_id)] = [{"role": "model", "parts": [{"text": "stale"}]}]
    await dialog_service.create_dialog(1, "Fresh 2")

    active_dialog_id = await db_manager.get_active_dialog_id(1)
    assert active_dialog_id is not None
    assert int(active_dialog_id) not in gemini_history_cache.dialog_chats_cache
