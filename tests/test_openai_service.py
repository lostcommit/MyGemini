import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_openai_service_generate_response_persists_turn(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.openai_service", None)
    openai_service = importlib.import_module("services.openai_service")
    openai_service = importlib.reload(openai_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_openai_api_key(1, "openai-secret")
    await db_manager.set_user_openai_model(1, "gpt-4.1-mini")
    dialog_id = await db_manager.get_active_dialog_id(1)
    assert dialog_id is not None

    async def fake_request(api_key, url, payload=None, method='POST'):
        assert api_key == "openai-secret"
        assert payload["model"] == "gpt-4.1-mini"
        return {
            "usage": {"prompt_tokens": 9, "completion_tokens": 3, "total_tokens": 12},
            "choices": [{"message": {"content": "hello from openai"}}],
        }

    openai_service._make_openai_request_async = fake_request

    response_text, sources = await openai_service.generate_response(1, "hi")
    history = await db_manager.get_conversation_history(dialog_id)
    usage = await db_manager.get_token_usage_by_period(1, "today")

    assert response_text == "hello from openai"
    assert sources == []
    assert history[-2]["message_text"] == "hi"
    assert history[-1]["message_text"] == "hello from openai"
    assert usage == {"prompt_tokens": 9, "completion_tokens": 3, "total_tokens": 12}
