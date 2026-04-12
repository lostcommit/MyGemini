from typing import Optional, Tuple

from config.settings import BOT_PERSONAS, BOT_STYLES, DEFAULT_LLM_BACKEND, DEFAULT_MODEL_ID, OPENAI_API_KEY, OPENAI_DEFAULT_MODEL
from database import db_manager
from . import dialog_service, llm_service
from .llm_backends import BACKEND_DISPLAY_NAMES, GEMINI_BACKEND, OPENAI_BACKEND, is_supported_backend


async def set_language(user_id: int, lang_code: str) -> str:
    await db_manager.set_user_language(user_id, lang_code)
    return lang_code


async def set_style(user_id: int, style_code: str) -> bool:
    if style_code not in BOT_STYLES:
        return False
    await db_manager.set_user_bot_style(user_id, style_code)
    return True


async def set_persona(user_id: int, persona_id: str, lang_code: str) -> Optional[str]:
    if persona_id not in BOT_PERSONAS:
        return None
    await db_manager.set_user_persona(user_id, persona_id)
    persona_info = BOT_PERSONAS[persona_id]
    return persona_info.get(f"name_{lang_code}", persona_info['name_ru'])


async def get_user_backend(user_id: int) -> str:
    backend = await db_manager.get_user_llm_backend(user_id)
    return backend if is_supported_backend(backend) else DEFAULT_LLM_BACKEND


async def get_backend_display_name_for_user(user_id: int) -> str:
    backend = await get_user_backend(user_id)
    return BACKEND_DISPLAY_NAMES.get(backend, backend)


async def get_current_api_key(user_id: int) -> Optional[str]:
    backend = await get_user_backend(user_id)
    if backend == GEMINI_BACKEND:
        return await db_manager.get_user_api_key(user_id)
    if backend == OPENAI_BACKEND:
        return await db_manager.get_user_openai_api_key(user_id) or OPENAI_API_KEY
    return None


async def get_default_model_for_backend(backend: str) -> Optional[str]:
    if backend == GEMINI_BACKEND:
        return DEFAULT_MODEL_ID
    if backend == OPENAI_BACKEND:
        return OPENAI_DEFAULT_MODEL
    return None


async def get_current_model(user_id: int) -> Optional[str]:
    backend = await get_user_backend(user_id)
    if backend == GEMINI_BACKEND:
        return await db_manager.get_user_gemini_model(user_id)
    if backend == OPENAI_BACKEND:
        return await db_manager.get_user_openai_model(user_id)
    return None


async def get_effective_model(user_id: int) -> Optional[str]:
    backend = await get_user_backend(user_id)
    return await get_current_model(user_id) or await get_default_model_for_backend(backend)


async def set_backend(user_id: int, backend: str) -> bool:
    if not is_supported_backend(backend):
        return False
    changed = await db_manager.set_user_llm_backend(user_id, backend)
    if changed:
        await dialog_service.reset_active_dialog_cache(user_id)
    return changed


async def get_backend_selection_context(user_id: int) -> Tuple[list, str]:
    current_backend = await get_user_backend(user_id)
    backends = [
        {"id": GEMINI_BACKEND, "display_name": BACKEND_DISPLAY_NAMES[GEMINI_BACKEND]},
        {"id": OPENAI_BACKEND, "display_name": BACKEND_DISPLAY_NAMES[OPENAI_BACKEND]},
    ]
    return backends, current_backend


async def set_model(user_id: int, model_name: str) -> str:
    backend = await get_user_backend(user_id)
    if backend == GEMINI_BACKEND:
        await db_manager.set_user_gemini_model(user_id, model_name)
    elif backend == OPENAI_BACKEND:
        await db_manager.set_user_openai_model(user_id, model_name)
    return model_name


async def validate_and_store_api_key(user_id: int, api_key: str) -> bool:
    backend = await get_user_backend(user_id)
    is_valid = await llm_service.validate_api_key_for_backend(backend, api_key)
    if not is_valid:
        return False

    if backend == GEMINI_BACKEND:
        await db_manager.set_user_api_key(user_id, api_key)
    elif backend == OPENAI_BACKEND:
        await db_manager.set_user_openai_api_key(user_id, api_key)

    await dialog_service.reset_active_dialog_cache(user_id)
    return True


async def reset_user_api_key(user_id: int) -> bool:
    backend = await get_user_backend(user_id)
    if backend == GEMINI_BACKEND:
        return await db_manager.set_user_api_key(user_id, None)
    if backend == OPENAI_BACKEND:
        return await db_manager.set_user_openai_api_key(user_id, None)
    return False


async def get_model_selection_context(user_id: int) -> Tuple[Optional[list], Optional[str]]:
    backend = await get_user_backend(user_id)
    if backend == GEMINI_BACKEND:
        current_model = await db_manager.get_user_gemini_model(user_id)
    elif backend == OPENAI_BACKEND:
        current_model = await db_manager.get_user_openai_model(user_id)
    else:
        return None, None

    api_key = await get_current_api_key(user_id)
    if not api_key:
        return None, None

    models = await llm_service.get_available_models_for_backend(backend, api_key)
    return models, current_model
