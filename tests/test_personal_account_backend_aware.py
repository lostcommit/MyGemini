import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_personal_account_shows_openai_backend_and_model(load_db_module):
    db_manager = load_db_module

    for module_name in [
        "services.settings_service",
        "services.llm_service",
        "features.personal_account",
    ]:
        sys.modules.pop(module_name, None)

    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)
    llm_service = importlib.import_module("services.llm_service")
    llm_service = importlib.reload(llm_service)
    personal_account = importlib.import_module("features.personal_account")
    personal_account = importlib.reload(personal_account)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_language(1, "ru")
    await db_manager.set_user_persona(1, "default")
    await db_manager.set_user_llm_backend(1, "openai")
    await db_manager.set_user_openai_api_key(1, "openai-secret")
    await db_manager.set_user_openai_model(1, "gpt-4.1")

    active_dialog_id = await db_manager.get_active_dialog_id(1)
    await db_manager.store_message(1, active_dialog_id, "user", "Давай обсудим музыку и гастроли")

    async def fake_generate_content_simple(backend, api_key, prompt):
        assert backend == "openai"
        assert api_key == "openai-secret"
        assert "музыку" in prompt
        return "Чаще всего в этом диалоге вы обсуждаете музыку и гастроли."

    llm_service.generate_content_simple = fake_generate_content_simple
    personal_account.llm_service.generate_content_simple = fake_generate_content_simple

    info_text = await personal_account.get_personal_account_info(1)

    assert "Backend / Backend:** Google Gemini" not in info_text
    assert "Backend / Backend:** OpenAI" in info_text
    assert "Модель / Model:** gpt-4.1" in info_text
    assert "API Key:** ✅ Установлен / Set" in info_text
    assert "обсуждаете музыку и гастроли" in info_text


@pytest.mark.asyncio
async def test_settings_service_returns_backend_specific_default_model(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.settings_service", None)
    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(2, "bob", "Bob", None)
    await db_manager.set_user_llm_backend(2, "openai")

    assert await settings_service.get_current_model(2) is None
    assert await settings_service.get_effective_model(2) == "gpt-4.1-mini"
