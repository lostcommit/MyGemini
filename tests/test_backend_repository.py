import importlib
import sqlite3
import sys

import pytest


@pytest.mark.asyncio
async def test_new_user_gets_default_llm_backend(load_db_module):
    db_manager = load_db_module

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    assert await db_manager.get_user_llm_backend(1) == "gemini"
    assert await db_manager.get_user_openai_api_key(1) is None
    assert await db_manager.get_user_openai_model(1) is None


@pytest.mark.asyncio
async def test_can_store_openai_backend_fields(load_db_module):
    db_manager = load_db_module

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    assert await db_manager.set_user_llm_backend(1, "openai") is True
    assert await db_manager.set_user_openai_api_key(1, "openai-secret") is True
    assert await db_manager.set_user_openai_model(1, "gpt-4.1-mini") is True

    assert await db_manager.get_user_llm_backend(1) == "openai"
    assert await db_manager.get_user_openai_api_key(1) == "openai-secret"
    assert await db_manager.get_user_openai_model(1) == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_default_llm_backend_env_is_used_for_new_users(configured_env, monkeypatch, tmp_path):
    monkeypatch.setenv("DEFAULT_LLM_BACKEND", "openai")

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
    ]:
        sys.modules.pop(module_name, None)

    telegram_helpers_stub = importlib.import_module("types").ModuleType("handlers.telegram_helpers")

    async def _notify_admin_of_new_user(*args, **kwargs):
        return None

    telegram_helpers_stub.notify_admin_of_new_user = _notify_admin_of_new_user
    sys.modules["handlers.telegram_helpers"] = telegram_helpers_stub

    db_manager = importlib.import_module("database.db_manager")
    db_manager = importlib.reload(db_manager)
    db_manager.set_database_name(str(tmp_path / "bot_database.db"))

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    assert await db_manager.get_user_llm_backend(1) == "openai"


@pytest.mark.asyncio
async def test_setup_database_migrates_legacy_users_table(load_db_module):
    db_manager = load_db_module

    db_path = db_manager.DATABASE_NAME
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                bot_style TEXT DEFAULT 'default' NOT NULL,
                first_interaction_date TEXT,
                api_key TEXT DEFAULT NULL,
                language_code TEXT DEFAULT 'ru' NOT NULL,
                gemini_model TEXT DEFAULT NULL,
                active_persona TEXT DEFAULT 'default' NOT NULL,
                active_dialog_id INTEGER,
                is_blocked INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    await db_manager.setup_database()

    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    finally:
        conn.close()

    assert {"llm_backend", "openai_api_key", "openai_model"}.issubset(columns)
