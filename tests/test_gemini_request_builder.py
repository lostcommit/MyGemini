import importlib
import sys

import pytest
from PIL import Image


@pytest.mark.asyncio
async def test_build_generate_content_request_adds_system_instruction(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.gemini_request_builder", None)
    request_builder = importlib.import_module("services.gemini_request_builder")
    request_builder = importlib.reload(request_builder)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_language(1, "en")
    await db_manager.set_user_persona(1, "default")
    await db_manager.set_user_bot_style(1, "concise")

    data = await request_builder.build_generate_content_request(
        user_id=1,
        model_name="gemini-2.5-pro",
        history=[],
        prompt="Hello",
    )

    assert data["payload"]["contents"] == [{"role": "user", "parts": [{"text": "Hello"}]}]
    assert data["payload"]["system_instruction"]["parts"][0]["text"] == (
        "Your answers must be as short and to the point as possible."
    )


@pytest.mark.asyncio
async def test_build_generate_content_request_adds_search_tool_when_supported(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.gemini_request_builder", None)
    request_builder = importlib.import_module("services.gemini_request_builder")
    request_builder = importlib.reload(request_builder)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    data = await request_builder.build_generate_content_request(
        user_id=1,
        model_name="gemini-2.5-flash",
        history=[],
        prompt="What time is it?",
    )

    assert data["supports_search"] is True
    assert data["payload"]["tools"] == [{"google_search": {}}]


def test_build_user_prompt_parts_for_image_caption():
    request_builder = importlib.import_module("services.gemini_request_builder")
    request_builder = importlib.reload(request_builder)

    image = Image.new("RGB", (4, 4), color="red")
    user_parts, user_message_for_db = request_builder.build_user_prompt_parts([image, "caption"])

    assert user_message_for_db == "[Изображение] caption"
    assert user_parts[0]["inline_data"]["mime_type"] == "image/jpeg"
    assert user_parts[1] == {"text": "caption"}
