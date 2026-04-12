import importlib
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FERNET_TEST_KEY = "0VXUK0t4hID6V6mdx8Z_Q37mo2J6Q7V_PvL8B6mNfho="


@pytest.fixture
def configured_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123456:TEST_TOKEN")
    monkeypatch.setenv("ENCRYPTION_KEY", FERNET_TEST_KEY)
    monkeypatch.setenv("DEFAULT_MODEL_ID", "gemini-2.5-flash")
    monkeypatch.delenv("ADMIN_USER_ID", raising=False)
    monkeypatch.delenv("GEMINI_MODEL_NAME", raising=False)


@pytest.fixture
def load_settings(configured_env):
    sys.modules.pop("config.settings", None)
    settings = importlib.import_module("config.settings")
    return importlib.reload(settings)


@pytest.fixture
def load_db_module(configured_env, tmp_path):
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
        "services.prompt_builder",
        "services.gemini_request_builder",
        "services.gemini_client",
        "services.gemini_response_parser",
        "services.gemini_persistence",
        "services.gemini_runtime_context",
        "services.gemini_history_cache",
        "services.openai_client",
        "services.openai_runtime_context",
        "services.openai_request_builder",
        "services.openai_response_parser",
        "services.openai_service",
        "services.llm_backends",
        "services.llm_service",
        "utils.markup_helpers",
    ]:
        sys.modules.pop(module_name, None)

    telegram_helpers_stub = types.ModuleType("handlers.telegram_helpers")

    async def _notify_admin_of_new_user(*args, **kwargs):
        return None

    telegram_helpers_stub.notify_admin_of_new_user = _notify_admin_of_new_user
    sys.modules["handlers.telegram_helpers"] = telegram_helpers_stub

    db_manager = importlib.import_module("database.db_manager")
    db_manager = importlib.reload(db_manager)
    db_manager.set_database_name(str(tmp_path / "bot_database.db"))
    return db_manager


@pytest.fixture
def load_gemini_and_db(configured_env, tmp_path):
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
        "services.prompt_builder",
        "services.gemini_request_builder",
        "services.gemini_client",
        "services.gemini_response_parser",
        "services.gemini_persistence",
        "services.gemini_runtime_context",
        "services.gemini_history_cache",
        "services.openai_client",
        "services.openai_runtime_context",
        "services.openai_request_builder",
        "services.openai_response_parser",
        "services.openai_service",
        "services.llm_backends",
        "services.llm_service",
        "utils.markup_helpers",
        "services.gemini_service",
    ]:
        sys.modules.pop(module_name, None)

    telegram_helpers_stub = types.ModuleType("handlers.telegram_helpers")

    async def _notify_admin_of_new_user(*args, **kwargs):
        return None

    telegram_helpers_stub.notify_admin_of_new_user = _notify_admin_of_new_user
    sys.modules["handlers.telegram_helpers"] = telegram_helpers_stub

    db_manager = importlib.import_module("database.db_manager")
    db_manager = importlib.reload(db_manager)
    db_manager.set_database_name(str(tmp_path / "bot_database.db"))

    gemini_history_cache = importlib.import_module("services.gemini_history_cache")
    gemini_history_cache = importlib.reload(gemini_history_cache)
    gemini_history_cache.dialog_chats_cache.clear()

    gemini_service = importlib.import_module("services.gemini_service")
    gemini_service = importlib.reload(gemini_service)

    return gemini_service, db_manager
