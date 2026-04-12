import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_persona_prompt_preferred_over_style(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.prompt_builder", None)
    prompt_builder = importlib.import_module("services.prompt_builder")
    prompt_builder = importlib.reload(prompt_builder)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_language(1, "en")
    await db_manager.set_user_persona(1, "python_expert")
    await db_manager.set_user_bot_style(1, "formal")

    prompt = await prompt_builder.get_system_instruction_text(1)

    assert prompt is not None
    assert "lead Python developer" in prompt


@pytest.mark.asyncio
async def test_style_prompt_used_when_persona_default(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.prompt_builder", None)
    prompt_builder = importlib.import_module("services.prompt_builder")
    prompt_builder = importlib.reload(prompt_builder)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_language(1, "en")
    await db_manager.set_user_persona(1, "default")
    await db_manager.set_user_bot_style(1, "concise")

    prompt = await prompt_builder.get_system_instruction_text(1)

    assert prompt == "Your answers must be as short and to the point as possible."
