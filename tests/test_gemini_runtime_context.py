import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_load_runtime_context_requires_api_key(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.gemini_runtime_context", None)
    runtime_context = importlib.import_module("services.gemini_runtime_context")
    runtime_context = importlib.reload(runtime_context)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    async def history_loader(dialog_id):
        return []

    with pytest.raises(runtime_context.GeminiAPIError):
        await runtime_context.load_runtime_context(1, history_loader=history_loader)


@pytest.mark.asyncio
async def test_load_runtime_context_loads_history_for_stateful_model(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.gemini_runtime_context", None)
    runtime_context = importlib.import_module("services.gemini_runtime_context")
    runtime_context = importlib.reload(runtime_context)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_api_key(1, "secret")
    await db_manager.set_user_gemini_model(1, "gemini-2.5-flash")
    dialog_id = await db_manager.get_active_dialog_id(1)

    calls = []

    async def history_loader(seen_dialog_id):
        calls.append(seen_dialog_id)
        return [{"role": "user", "parts": [{"text": "hi"}]}]

    data = await runtime_context.load_runtime_context(1, history_loader=history_loader)

    assert data["api_key"] == "secret"
    assert data["active_dialog_id"] == dialog_id
    assert data["model_name"] == "gemini-2.5-flash"
    assert data["stateless"] is False
    assert data["history"] == [{"role": "user", "parts": [{"text": "hi"}]}]
    assert calls == [dialog_id]


@pytest.mark.asyncio
async def test_load_runtime_context_skips_history_for_stateless_model(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.gemini_runtime_context", None)
    runtime_context = importlib.import_module("services.gemini_runtime_context")
    runtime_context = importlib.reload(runtime_context)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_api_key(1, "secret")
    await db_manager.set_user_gemini_model(1, "gemma-3-27b-it")

    calls = []

    async def history_loader(seen_dialog_id):
        calls.append(seen_dialog_id)
        return [{"role": "user", "parts": [{"text": "hi"}]}]

    data = await runtime_context.load_runtime_context(1, history_loader=history_loader)

    assert data["stateless"] is True
    assert data["history"] == []
    assert calls == []
