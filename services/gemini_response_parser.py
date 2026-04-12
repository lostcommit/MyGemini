from typing import Any, Dict, List

from .gemini_client import GeminiAPIError


def extract_usage_metadata(response_json: Dict[str, Any]) -> Dict[str, int]:
    usage_metadata = response_json.get('usageMetadata', {}) if response_json else {}
    return {
        'prompt_tokens': usage_metadata.get('promptTokenCount', 0),
        'completion_tokens': usage_metadata.get('candidatesTokenCount', 0),
        'total_tokens': usage_metadata.get('totalTokenCount', 0),
    }


def extract_sources(first_candidate: Dict[str, Any]) -> List[Dict[str, str]]:
    sources: List[Dict[str, str]] = []
    metadata = first_candidate.get('groundingMetadata', {})

    if 'groundingAttributions' in metadata:
        for attr in metadata['groundingAttributions']:
            if 'web' in attr and attr['web'].get('uri') and attr['web'].get('title'):
                sources.append({"uri": attr['web']['uri'], "title": attr['web']['title']})
    elif 'groundingChunks' in metadata:
        for chunk in metadata['groundingChunks']:
            if 'web' in chunk and chunk['web'].get('uri') and chunk['web'].get('title'):
                source_item = {"uri": chunk['web']['uri'], "title": chunk['web']['title']}
                if source_item not in sources:
                    sources.append(source_item)

    return sources


def parse_generate_content_response(response_json: Dict[str, Any]) -> Dict[str, Any]:
    if not response_json or "candidates" not in response_json:
        raise GeminiAPIError("Ответ API не содержит 'candidates'.", details=response_json)

    first_candidate = response_json["candidates"][0]

    if first_candidate.get("finishReason") == "SAFETY":
        raise GeminiAPIError("Ответ заблокирован настройками безопасности.", details={"finish_reason": "SAFETY"})

    response_text = "".join(
        part.get("text", "")
        for part in first_candidate.get("content", {}).get("parts", [])
    ).strip()

    return {
        'response_text': response_text,
        'sources': extract_sources(first_candidate),
        'usage': extract_usage_metadata(response_json),
    }


def parse_simple_text_response(response_json: Dict[str, Any]) -> str:
    try:
        return response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise GeminiAPIError(f"Ошибка чтения ответа от API: {e}", details={"error": {"message": "parsing_error"}})
