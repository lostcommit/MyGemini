import pytest


@pytest.mark.asyncio
async def test_start_fresh_dialog_creates_new_active_dialog(load_db_module):
    db_manager = load_db_module
    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", "Example")

    original_dialog_id = await db_manager.get_active_dialog_id(1)
    assert original_dialog_id is not None

    await db_manager.store_message(1, original_dialog_id, "user", "old context")

    fresh_dialog_id = await db_manager.start_fresh_dialog(1, "Fresh dialog")
    active_dialog_id = await db_manager.get_active_dialog_id(1)

    assert fresh_dialog_id is not None
    assert active_dialog_id == fresh_dialog_id
    assert fresh_dialog_id != original_dialog_id

    old_history = await db_manager.get_conversation_history(original_dialog_id)
    new_history = await db_manager.get_conversation_history(fresh_dialog_id)

    assert [item["message_text"] for item in old_history] == ["old context"]
    assert new_history == []


@pytest.mark.asyncio
async def test_set_active_dialog_rejects_foreign_dialog(load_db_module):
    db_manager = load_db_module
    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.add_or_update_user(2, "bob", "Bob", None)

    alice_dialog = await db_manager.get_active_dialog_id(1)
    bob_dialog = await db_manager.get_active_dialog_id(2)
    assert alice_dialog is not None and bob_dialog is not None

    changed = await db_manager.set_active_dialog(1, bob_dialog)
    active_dialog_after = await db_manager.get_active_dialog_id(1)

    assert changed is False
    assert active_dialog_after == alice_dialog


@pytest.mark.asyncio
async def test_failed_gemini_call_does_not_persist_user_turn(load_gemini_and_db):
    gemini_service, db_manager = load_gemini_and_db
    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_api_key(1, "secret-key")
    active_dialog_id = await db_manager.get_active_dialog_id(1)
    assert active_dialog_id is not None

    async def boom(*args, **kwargs):
        raise gemini_service.GeminiAPIError("boom", details={"error": {"message": "service_unavailable"}})

    gemini_service._make_gemini_request_async = boom

    with pytest.raises(gemini_service.GeminiAPIError):
        await gemini_service.generate_response(1, "Hello")

    history = await db_manager.get_conversation_history(active_dialog_id)
    assert history == []


def test_default_model_id_falls_back_to_legacy_env_name(configured_env, monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL_ID", raising=False)
    monkeypatch.setenv("GEMINI_MODEL_NAME", "gemini-legacy-model")

    import importlib
    import sys

    sys.modules.pop("config.settings", None)
    settings = importlib.import_module("config.settings")
    settings = importlib.reload(settings)

    assert settings.DEFAULT_MODEL_ID == "gemini-legacy-model"
