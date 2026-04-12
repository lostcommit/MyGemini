import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_validate_and_store_api_key_resets_dialog_cache_for_gemini(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.settings_service", None)
    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "gemini")
    active_dialog_id = await db_manager.get_active_dialog_id(1)
    assert active_dialog_id is not None

    calls = []

    async def ok(_backend: str, _api_key: str) -> bool:
        return True

    async def reset_cache(user_id: int):
        calls.append(user_id)
        return active_dialog_id

    settings_service.llm_service.validate_api_key_for_backend = ok
    settings_service.dialog_service.reset_active_dialog_cache = reset_cache

    stored = await settings_service.validate_and_store_api_key(1, "secret")

    assert stored is True
    assert calls == [1]
    assert await db_manager.get_user_api_key(1) == "secret"


@pytest.mark.asyncio
async def test_validate_and_store_api_key_uses_openai_slot_for_openai_backend(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.settings_service", None)
    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "openai")

    async def ok(_backend: str, _api_key: str) -> bool:
        return True

    settings_service.llm_service.validate_api_key_for_backend = ok

    stored = await settings_service.validate_and_store_api_key(1, "openai-secret")

    assert stored is True
    assert await db_manager.get_user_openai_api_key(1) == "openai-secret"
    assert await db_manager.get_user_api_key(1) is None


@pytest.mark.asyncio
async def test_get_current_api_key_uses_openai_env_fallback(configured_env, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

    for module_name in [
        "config.settings",
        "utils.crypto_helpers",
        "handlers.telegram_helpers",
        "database.core",
        "database.migrations",
        "database.dialogs_repo",
        "database.conversations_repo",
        "database.settings_repo",
        "database.users_repo",
        "database.admin_repo",
        "database.db_manager",
        "services.settings_service",
    ]:
        sys.modules.pop(module_name, None)

    import types
    telegram_helpers_stub = types.ModuleType("handlers.telegram_helpers")

    async def _notify_admin_of_new_user(*args, **kwargs):
        return None

    telegram_helpers_stub.notify_admin_of_new_user = _notify_admin_of_new_user
    sys.modules["handlers.telegram_helpers"] = telegram_helpers_stub

    db_manager = importlib.import_module("database.db_manager")
    db_manager = importlib.reload(db_manager)
    db_manager.set_database_name(str(tmp_path / "bot_database.db"))

    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "openai")

    assert await settings_service.get_current_api_key(1) == "env-openai-key"


@pytest.mark.asyncio
async def test_set_persona_returns_localized_persona_name(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.settings_service", None)
    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    persona_name = await settings_service.set_persona(1, "python_expert", "en")

    assert persona_name == "🐍 Python Expert"
    assert await db_manager.get_user_persona(1) == "python_expert"


@pytest.mark.asyncio
async def test_set_backend_updates_user_backend_and_resets_cache(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.settings_service", None)
    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    calls = []

    async def reset_cache(user_id: int):
        calls.append((user_id, "reset"))
        return await db_manager.get_active_dialog_id(user_id)

    settings_service.dialog_service.reset_active_dialog_cache = reset_cache

    changed = await settings_service.set_backend(1, "openai")

    assert changed is True
    assert await db_manager.get_user_llm_backend(1) == "openai"
    assert calls == [(1, "reset")]
