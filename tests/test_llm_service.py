import importlib
import sys

import pytest


@pytest.mark.asyncio
async def test_get_user_backend_defaults_to_gemini(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.llm_service", None)
    llm_service = importlib.import_module("services.llm_service")
    llm_service = importlib.reload(llm_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)

    assert await llm_service.get_user_backend(1) == "gemini"


@pytest.mark.asyncio
async def test_generate_response_routes_to_gemini_backend(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.llm_service", None)
    llm_service = importlib.import_module("services.llm_service")
    llm_service = importlib.reload(llm_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "gemini")

    async def fake_generate_response(user_id, prompt):
        return f"gemini:{user_id}:{prompt}", []

    llm_service.gemini_service.generate_response = fake_generate_response

    response_text, sources = await llm_service.generate_response(1, "hello")
    assert response_text == "gemini:1:hello"
    assert sources == []


@pytest.mark.asyncio
async def test_generate_response_routes_to_openai_backend(load_db_module):
    db_manager = load_db_module

    sys.modules.pop("services.llm_service", None)
    llm_service = importlib.import_module("services.llm_service")
    llm_service = importlib.reload(llm_service)

    await db_manager.setup_database()
    await db_manager.add_or_update_user(1, "alice", "Alice", None)
    await db_manager.set_user_llm_backend(1, "openai")

    async def fake_generate_response(user_id, prompt):
        return f"openai:{user_id}:{prompt}", []

    llm_service.openai_service.generate_response = fake_generate_response

    response_text, sources = await llm_service.generate_response(1, "hello")
    assert response_text == "openai:1:hello"
    assert sources == []


@pytest.mark.asyncio
async def test_validate_api_key_for_backend_routes_to_gemini(load_db_module):
    load_db_module

    sys.modules.pop("services.llm_service", None)
    llm_service = importlib.import_module("services.llm_service")
    llm_service = importlib.reload(llm_service)

    async def fake_validate_api_key(api_key):
        return api_key == "ok"

    llm_service.gemini_service.validate_api_key = fake_validate_api_key

    assert await llm_service.validate_api_key_for_backend("gemini", "ok") is True
    assert await llm_service.validate_api_key_for_backend("gemini", "bad") is False
