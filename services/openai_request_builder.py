import base64
from io import BytesIO
from typing import Any, Dict, List, Tuple, Union

import PIL.Image

from .openai_client import OPENAI_API_BASE_URL, OpenAIAPIError
from .prompt_builder import get_system_instruction_text

OPENAI_MODELS = [
    {"name": "gpt-4.1-mini", "display_name": "GPT-4.1 mini"},
    {"name": "gpt-4.1", "display_name": "GPT-4.1"},
    {"name": "gpt-4o-mini", "display_name": "GPT-4o mini"},
    {"name": "gpt-4o", "display_name": "GPT-4o"},
]


def build_user_message_content(
    prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]]
) -> Tuple[Union[str, List[Dict[str, Any]]], str]:
    if isinstance(prompt, str):
        return prompt, prompt

    content: List[Dict[str, Any]] = []
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
            image_data = base64.b64encode(buffered.getvalue()).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
            })
        elif isinstance(item, bytes):
            raise OpenAIAPIError(
                "Voice messages are not supported for OpenAI backend yet.",
                details={"error": {"message": "openai_voice_not_supported"}},
            )

    if text_part:
        content.insert(0, {"type": "text", "text": text_part})

    if media_type == "image":
        user_message_for_db = f"[Изображение] {text_part}".strip()
    else:
        user_message_for_db = text_part

    return content, user_message_for_db


def convert_history_to_messages(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    for item in history:
        role = 'assistant' if item.get('role') == 'bot' else 'user'
        messages.append({"role": role, "content": item.get('message_text', '')})
    return messages


async def build_chat_completions_request(
    user_id: int,
    model_name: str,
    history: List[Dict[str, Any]],
    prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]],
) -> Dict[str, Any]:
    messages = convert_history_to_messages(history)
    system_instruction_text = await get_system_instruction_text(user_id)
    if system_instruction_text:
        messages.insert(0, {"role": "system", "content": system_instruction_text})

    user_content, user_message_for_db = build_user_message_content(prompt)
    messages.append({"role": "user", "content": user_content})

    return {
        'url': f"{OPENAI_API_BASE_URL}/chat/completions",
        'payload': {
            'model': model_name,
            'messages': messages,
        },
        'user_message_for_db': user_message_for_db,
    }
