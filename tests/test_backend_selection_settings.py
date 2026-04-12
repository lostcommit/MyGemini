import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_get_backend_selection_context_returns_current_backend(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.settings_service", None)
    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "openai")

    backends, current_backend = await settings_service.get_backend_selection_context(1)

    assert current_backend == "openai"
    assert {item["id"] for item in backends} == {"gemini", "openai"}


@pytest.mark.asyncio
async def test_create_settings_keyboard_shows_current_backend(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("utils.markup_helpers", None)
    markup_helpers = importlib.import_module("utils.markup_helpers")
    markup_helpers = importlib.reload(markup_helpers)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "openai")

    keyboard = await markup_helpers.create_settings_keyboard(1)
    button_texts = [button.text for row in keyboard.keyboard for button in row]

    assert any("OpenAI" in text for text in button_texts)


@pytest.mark.asyncio
async def test_create_backend_selection_keyboard_marks_current_backend(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("utils.markup_helpers", None)
    markup_helpers = importlib.import_module("utils.markup_helpers")
    markup_helpers = importlib.reload(markup_helpers)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "openai")

    keyboard = await markup_helpers.create_backend_selection_keyboard(1)
    button_texts = [button.text for row in keyboard.keyboard for button in row]

    assert any(text.startswith("✅ OpenAI") for text in button_texts)
