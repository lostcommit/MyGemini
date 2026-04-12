import PIL.Image
from typing import Dict, List, Tuple, Union

from logger_config import get_logger
from .gemini_persistence import persist_conversation_turn
from .openai_client import (
    OPENAI_API_BASE_URL,
    OpenAIAPIError,
    close_http_session,
    init_http_session,
    make_openai_request_async,
)
from .openai_request_builder import OPENAI_MODELS, build_chat_completions_request
from .openai_response_parser import parse_chat_completions_response, parse_models_response
from .openai_runtime_context import DEFAULT_OPENAI_MODEL, load_runtime_context

openai_logger = get_logger('openai_api')

_make_openai_request_async = make_openai_request_async


async def generate_response(user_id: int, prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]]) -> Tuple[str, List[Dict[str, str]]]:
    runtime_context = await load_runtime_context(user_id, logger=openai_logger)
    api_key = runtime_context['api_key']
    active_dialog_id = runtime_context['active_dialog_id']
    model_name = runtime_context['model_name']
    history = runtime_context['history']

    request_data = await build_chat_completions_request(
        user_id=user_id,
        model_name=model_name,
        history=history,
        prompt=prompt,
    )

    response_json = await _make_openai_request_async(api_key, request_data['url'], request_data['payload'])
    parsed_response = parse_chat_completions_response(response_json)

    await persist_conversation_turn(
        user_id=user_id,
        dialog_id=active_dialog_id,
        user_message_for_db=request_data['user_message_for_db'],
        response_text=parsed_response['response_text'],
        usage=parsed_response['usage'],
    )

    return parsed_response['response_text'], parsed_response['sources']


async def generate_content_simple(api_key: str, prompt: str) -> str:
    payload = {
        'model': DEFAULT_OPENAI_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    response_json = await _make_openai_request_async(api_key, f"{OPENAI_API_BASE_URL}/chat/completions", payload)
    return parse_chat_completions_response(response_json)['response_text']


async def validate_api_key(api_key: str) -> bool:
    try:
        response = await _make_openai_request_async(api_key, f"{OPENAI_API_BASE_URL}/models", method='GET')
        return response is not None and 'data' in response
    except OpenAIAPIError:
        return False


async def get_available_models(api_key: str) -> List[Dict[str, str]]:
    response_json = await _make_openai_request_async(api_key, f"{OPENAI_API_BASE_URL}/models", method='GET')
    available_ids = {item['id'] for item in parse_models_response(response_json)}
    return [item for item in OPENAI_MODELS if item['name'] in available_ids]
