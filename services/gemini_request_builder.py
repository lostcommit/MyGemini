import base64
from io import BytesIO
from typing import Any, Dict, List, Tuple, Union

import PIL.Image

from config.settings import GENERATION_CONFIG, MODELS_METADATA, SAFETY_SETTINGS
from .gemini_client import GEMINI_API_BASE_URL
from .prompt_builder import get_system_instruction_text

GOOGLE_SEARCH_TOOL = {
    "tools": [{"google_search": {}}]
}


def is_stateless_model(model_name: str) -> bool:
    return model_name.startswith('gemma')


def get_model_capabilities(model_name: str) -> Dict[str, bool]:
    model_meta = MODELS_METADATA.get(model_name, {})
    return {
        "supports_search": model_meta.get("supports_search", False),
        "supports_system_instruction": model_meta.get("supports_system_instruction", False),
    }


def build_user_prompt_parts(
    prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]]
) -> Tuple[List[Dict[str, Any]], str]:
    """Build Gemini user parts and the text representation persisted in DB."""
    user_parts: List[Dict[str, Any]] = []
    user_message_for_db = ""

    if isinstance(prompt, str):
        user_parts.append({"text": prompt})
        return user_parts, prompt

    text_part = ""
    media_type = None

    for item in prompt:
        if isinstance(item, str):
            text_part = item
        elif isinstance(item, PIL.Image.Image):
            media_type = "image"
            buffered = BytesIO()
            if item.mode == 'RGBA':
                item = item.convert('RGB')
            item.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_str}})
        elif isinstance(item, bytes):
            media_type = "audio"
            audio_str = base64.b64encode(item).decode('utf-8')
            user_parts.append({"inline_data": {"mime_type": "audio/ogg", "data": audio_str}})

    if text_part:
        user_parts.append({"text": text_part})

    if media_type == "image":
        user_message_for_db = f"[Изображение] {text_part}".strip()
    elif media_type == "audio":
        user_message_for_db = f"[Голосовое сообщение] {text_part}".strip()
    else:
        user_message_for_db = text_part

    return user_parts, user_message_for_db


async def build_generate_content_request(
    user_id: int,
    model_name: str,
    history: List[Dict[str, Any]],
    prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]],
) -> Dict[str, Any]:
    """Build URL, payload and persistence metadata for generateContent."""
    capabilities = get_model_capabilities(model_name)
    request_contents = list(history)
    user_parts, user_message_for_db = build_user_prompt_parts(prompt)
    request_contents.append({"role": "user", "parts": user_parts})

    payload: Dict[str, Any] = {
        "contents": request_contents,
        "generationConfig": GENERATION_CONFIG,
        "safetySettings": SAFETY_SETTINGS,
    }

    if capabilities["supports_search"]:
        payload.update(GOOGLE_SEARCH_TOOL)

    if capabilities["supports_system_instruction"]:
        system_instruction_text = await get_system_instruction_text(user_id)
        if system_instruction_text:
            payload["system_instruction"] = {"parts": [{"text": system_instruction_text}]}

    return {
        "url": f"{GEMINI_API_BASE_URL}/models/{model_name}:generateContent",
        "payload": payload,
        "user_parts": user_parts,
        "user_message_for_db": user_message_for_db,
        "supports_search": capabilities["supports_search"],
        "supports_system_instruction": capabilities["supports_system_instruction"],
    }
