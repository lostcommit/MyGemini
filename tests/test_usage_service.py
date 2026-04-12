import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_get_usage_context_returns_backend_display_and_effective_model(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.settings_service", None)
    sys.modules.pop("services.usage_service", None)
    settings_service = importlib.import_module("services.settings_service")
    settings_service = importlib.reload(settings_service)
    usage_service = importlib.import_module("services.usage_service")
    usage_service = importlib.reload(usage_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "openai")
    await db_manager.set_user_openai_model(1, "gpt-4.1")

    context = await usage_service.get_usage_context(settings_service, 1)

    assert context == {
        "backend": "openai",
        "backend_name": "OpenAI",
        "model_name": "gpt-4.1",
    }


def test_calculate_usage_cost_for_gemini_default_pricing(load_settings):
    sys.modules.pop("services.usage_service", None)
    usage_service = importlib.import_module("services.usage_service")
    usage_service = importlib.reload(usage_service)

    pricing = usage_service.get_pricing_for_backend_model("gemini", "unknown-model")
    cost = usage_service.calculate_usage_cost(
        {
            "prompt_tokens": 1_000_000,
            "completion_tokens": 1_000_000,
            "total_tokens": 2_000_000,
        },
        pricing,
    )

    assert pricing is not None
    assert cost == pytest.approx(1.40)


def test_calculate_usage_cost_returns_none_when_pricing_is_missing(load_settings):
    sys.modules.pop("services.usage_service", None)
    usage_service = importlib.import_module("services.usage_service")
    usage_service = importlib.reload(usage_service)

    pricing = usage_service.get_pricing_for_backend_model("openai", "gpt-4.1")
    cost = usage_service.calculate_usage_cost(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 2000,
            "total_tokens": 3000,
        },
        pricing,
    )

    assert pricing is None
    assert cost is None
