from typing import Any, Dict, List

from .openai_client import OpenAIAPIError


def extract_usage(response_json: Dict[str, Any]) -> Dict[str, int]:
    usage = response_json.get('usage', {}) if response_json else {}
    return {
        'prompt_tokens': usage.get('prompt_tokens', 0),
        'completion_tokens': usage.get('completion_tokens', 0),
        'total_tokens': usage.get('total_tokens', 0),
    }


def parse_chat_completions_response(response_json: Dict[str, Any]) -> Dict[str, Any]:
    if not response_json or 'choices' not in response_json or not response_json['choices']:
        raise OpenAIAPIError("OpenAI response does not contain choices.", details={"error": {"message": "parsing_error"}})

    first_choice = response_json['choices'][0]
    message = first_choice.get('message', {})
    content = message.get('content', '')

    if isinstance(content, list):
        response_text = ''.join(part.get('text', '') for part in content if isinstance(part, dict)).strip()
    else:
        response_text = str(content).strip()

    return {
        'response_text': response_text,
        'sources': [],
        'usage': extract_usage(response_json),
    }


def parse_models_response(response_json: Dict[str, Any]) -> List[Dict[str, str]]:
    data = response_json.get('data', []) if response_json else []
    return [{"id": item.get('id', '')} for item in data if item.get('id')]
