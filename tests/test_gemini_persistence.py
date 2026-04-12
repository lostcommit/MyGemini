import importlib
import sys

import pytest


def test_update_dialog_history_cache_appends_for_stateful_model(configured_env):
    persistence = importlib.import_module("services.gemini_persistence")
    persistence = importlib.reload(persistence)

    history = []
    user_parts = [{"text": "hello"}]

    persistence.update_dialog_history_cache(
        history,
        user_parts,
        "world",
        stateless=False,
    )

    assert history == [
        {"role": "user", "parts": [{"text": "hello"}]},
        {"role": "model", "parts": [{"text": "world"}]},
    ]


def test_update_dialog_history_cache_skips_for_stateless_model(configured_env):
    persistence = importlib.import_module("services.gemini_persistence")
    persistence = importlib.reload(persistence)

    history = []
    persistence.update_dialog_history_cache(
        history,
        [{"text": "hello"}],
        "world",
        stateless=True,
    )

    assert history == []


@pytest.mark.asyncio
async def test_persist_conversation_turn_stores_user_and_bot_messages(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.gemini_persistence", None)
    persistence = importlib.import_module("services.gemini_persistence")
    persistence = importlib.reload(persistence)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    dialog_id = await db_manager.get_active_dialog_id(1)
    assert dialog_id is not None

    await persistence.persist_conversation_turn(
        user_id=1,
        dialog_id=dialog_id,
        user_message_for_db="Hello",
        response_text="Hi there",
        usage={
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    )

    history = await db_manager.get_conversation_history(dialog_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["message_text"] == "Hello"
    assert history[1]["role"] == "bot"
    assert history[1]["message_text"] == "Hi there"

    usage = await db_manager.get_token_usage_by_period(1, "today")
    assert usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }
