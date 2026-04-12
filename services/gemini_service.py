# File: services/gemini_service.py
import PIL.Image
from typing import List, Union, Dict, Tuple

from config.settings import DEFAULT_MODEL_ID
from logger_config import get_logger
from .gemini_client import (
    GEMINI_API_BASE_URL,
    GeminiAPIError,
    close_http_session,
    init_http_session,
    make_gemini_request_async,
)
from .gemini_request_builder import build_generate_content_request
from .gemini_response_parser import (
    parse_generate_content_response,
    parse_simple_text_response,
)
from .gemini_persistence import (
    persist_conversation_turn,
    update_dialog_history_cache,
)
from .gemini_runtime_context import load_runtime_context
from .gemini_history_cache import (
    dialog_chats_cache,
    get_dialog_chat_history,
    reset_dialog_chat,
)

gemini_logger = get_logger('gemini_api')

# Backward-compatible alias for tests and legacy callers that monkeypatch the old symbol.
_make_gemini_request_async = make_gemini_request_async


async def generate_response(user_id: int, prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]]) -> Tuple[str, List[Dict[str, str]]]:
    """
    Генерирует ответ от Gemini, динамически включая функции.
    Для моделей Gemma история диалога игнорируется для совместимости.
    """
    runtime_context = await load_runtime_context(
        user_id,
        history_loader=get_dialog_chat_history,
        logger=gemini_logger,
    )
    api_key = runtime_context['api_key']
    active_dialog_id = runtime_context['active_dialog_id']
    model_name = runtime_context['model_name']
    is_gemma_model = runtime_context['stateless']
    history = runtime_context['history']

    request_data = await build_generate_content_request(
        user_id=user_id,
        model_name=model_name,
        history=history,
        prompt=prompt,
    )
    user_parts = request_data["user_parts"]
    user_message_for_db = request_data["user_message_for_db"]

    gemini_logger.info(
        f"Генерация: user={user_id}, model={model_name}, search={request_data['supports_search']}, "
        f"system_instr={request_data['supports_system_instruction']}, stateless={is_gemma_model}",
        extra={'user_id': str(user_id)}
    )

    try:
        response_json = await _make_gemini_request_async(api_key, request_data["url"], request_data["payload"])
        parsed_response = parse_generate_content_response(response_json)
        response_text = parsed_response['response_text']
        sources = parsed_response['sources']
        usage = parsed_response['usage']

        gemini_logger.info(
            "Получен ответ Gemini: user=%s model=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            user_id,
            model_name,
            usage['prompt_tokens'],
            usage['completion_tokens'],
            usage['total_tokens'],
            extra={'user_id': str(user_id)},
        )

        update_dialog_history_cache(
            history,
            user_parts,
            response_text,
            stateless=is_gemma_model,
        )

        await persist_conversation_turn(
            user_id=user_id,
            dialog_id=active_dialog_id,
            user_message_for_db=user_message_for_db,
            response_text=response_text,
            usage=usage,
        )

        return response_text, sources

    except GeminiAPIError:
        raise

async def generate_content_simple(api_key: str, prompt: str) -> str:
    """Генерирует ответ от Gemini без истории. Выбрасывает GeminiAPIError."""
    url = f"{GEMINI_API_BASE_URL}/models/{DEFAULT_MODEL_ID}:generateContent"
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    response_json = await _make_gemini_request_async(api_key, url, payload, 'POST')
    return parse_simple_text_response(response_json)

async def validate_api_key(api_key: str) -> bool:
    """Проверяет валидность API-ключа."""
    url = f"{GEMINI_API_BASE_URL}/models/{DEFAULT_MODEL_ID}:countTokens"
    payload = {"contents": [{"parts": [{"text": "hello"}]}]}
    try:
        response = await _make_gemini_request_async(api_key, url, payload, 'POST')
        return response is not None and "totalTokens" in response
    except GeminiAPIError:
        return False

async def get_available_models(api_key: str) -> List[Dict[str, str]]:
    """Получает список доступных моделей Gemini с API. Выбрасывает GeminiAPIError."""
    url = f"{GEMINI_API_BASE_URL}/models"
    response_json = await _make_gemini_request_async(api_key, url, method='GET')
    available_models = []
    if not response_json or 'models' not in response_json:
        return []

    for model in response_json['models']:
        model_name = model.get('name', '').replace('models/', '')
        if 'generateContent' in model.get('supportedGenerationMethods', []) and \
           'embedding' not in model_name and 'aqa' not in model_name and 'text-embedding' not in model_name:
            available_models.append({
                "name": model_name,
                "display_name": model.get('displayName', model_name)
            })

    available_models.sort(key=lambda x: ('flash' not in x['name'], 'pro' not in x['name'], x['name']))
    return available_models