from typing import Dict, List, Tuple, Union

import PIL.Image

from config.settings import DEFAULT_LLM_BACKEND
from database import db_manager
from . import gemini_service, openai_service
from .llm_backends import GEMINI_BACKEND, OPENAI_BACKEND, is_supported_backend

PromptType = Union[str, List[Union[str, PIL.Image.Image, bytes]]]


async def get_user_backend(user_id: int) -> str:
    backend = await db_manager.get_user_llm_backend(user_id)
    return backend if is_supported_backend(backend) else DEFAULT_LLM_BACKEND


async def set_user_backend(user_id: int, backend: str) -> bool:
    if not is_supported_backend(backend):
        return False
    return await db_manager.set_user_llm_backend(user_id, backend)


async def generate_response(user_id: int, prompt: PromptType) -> Tuple[str, List[Dict[str, str]]]:
    backend = await get_user_backend(user_id)
    if backend == GEMINI_BACKEND:
        return await gemini_service.generate_response(user_id, prompt)
    if backend == OPENAI_BACKEND:
        return await openai_service.generate_response(user_id, prompt)
    raise ValueError(f"Unsupported LLM backend: {backend}")


async def validate_api_key_for_backend(backend: str, api_key: str) -> bool:
    if backend == GEMINI_BACKEND:
        return await gemini_service.validate_api_key(api_key)
    if backend == OPENAI_BACKEND:
        return await openai_service.validate_api_key(api_key)
    raise ValueError(f"Unsupported LLM backend: {backend}")


async def get_available_models_for_backend(backend: str, api_key: str) -> List[Dict[str, str]]:
    if backend == GEMINI_BACKEND:
        return await gemini_service.get_available_models(api_key)
    if backend == OPENAI_BACKEND:
        return await openai_service.get_available_models(api_key)
    raise ValueError(f"Unsupported LLM backend: {backend}")


async def generate_content_simple(backend: str, api_key: str, prompt: str) -> str:
    if backend == GEMINI_BACKEND:
        return await gemini_service.generate_content_simple(api_key, prompt)
    if backend == OPENAI_BACKEND:
        return await openai_service.generate_content_simple(api_key, prompt)
    raise ValueError(f"Unsupported LLM backend: {backend}")
