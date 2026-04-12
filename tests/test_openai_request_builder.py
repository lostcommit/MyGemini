import importlib
import sys

import pytest
from PIL import Image


@pytest.mark.asyncio
async def test_build_chat_completions_request_adds_system_prompt_and_history(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.openai_request_builder", None)
    request_builder = importlib.import_module("services.openai_request_builder")
    request_builder = importlib.reload(request_builder)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_language(1, "en")
    await db_manager.set_user_bot_style(1, "concise")

    data = await request_builder.build_chat_completions_request(
        user_id=1,
        model_name="gpt-4.1-mini",
        history=[{"role": "user", "message_text": "old"}, {"role": "bot", "message_text": "answer"}],
        prompt="hello",
    )

    assert data["payload"]["model"] == "gpt-4.1-mini"
    assert data["payload"]["messages"][0]["role"] == "system"
    assert data["payload"]["messages"][1] == {"role": "user", "content": "old"}
    assert data["payload"]["messages"][2] == {"role": "assistant", "content": "answer"}
    assert data["payload"]["messages"][3] == {"role": "user", "content": "hello"}


def test_build_user_message_content_for_image_caption():
    request_builder = importlib.import_module("services.openai_request_builder")
    request_builder = importlib.reload(request_builder)

    image = Image.new("RGB", (4, 4), color="red")
    content, user_message_for_db = request_builder.build_user_message_content([image, "caption"])

    assert user_message_for_db == "[Изображение] caption"
    assert content[0] == {"type": "text", "text": "caption"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_build_user_message_content_rejects_voice():
    request_builder = importlib.import_module("services.openai_request_builder")
    request_builder = importlib.reload(request_builder)

    with pytest.raises(request_builder.OpenAIAPIError):
        request_builder.build_user_message_content([b"voice-bytes"])
