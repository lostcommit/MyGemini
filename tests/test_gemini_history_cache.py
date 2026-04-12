import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_get_dialog_chat_history_loads_and_caches_db_history(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.gemini_history_cache", None)
    history_cache = importlib.import_module("services.gemini_history_cache")
    history_cache = importlib.reload(history_cache)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    dialog_id = await db_manager.get_active_dialog_id(1)
    assert dialog_id is not None

    await db_manager.store_message(1, dialog_id, "user", "hello")
    await db_manager.store_message(1, dialog_id, "bot", "world")

    history = await history_cache.get_dialog_chat_history(dialog_id)
    assert history == [
        {"role": "user", "parts": [{"text": "hello"}]},
        {"role": "model", "parts": [{"text": "world"}]},
    ]

    await db_manager.store_message(1, dialog_id, "user", "new message")
    cached_history = await history_cache.get_dialog_chat_history(dialog_id)
    assert cached_history == history


def test_reset_dialog_chat_removes_cached_entry(configured_env):
    history_cache = importlib.import_module("services.gemini_history_cache")
    history_cache = importlib.reload(history_cache)

    history_cache.dialog_chats_cache[123] = [{"role": "model", "parts": [{"text": "stale"}]}]
    history_cache.reset_dialog_chat(123)

    assert 123 not in history_cache.dialog_chats_cache
