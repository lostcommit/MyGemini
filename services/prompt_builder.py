from typing import Optional

from config.settings import BOT_PERSONAS
from database import db_manager


_STYLE_PROMPTS = {
    'formal': "You must answer in a strictly formal and business-like manner.",
    'informal': "You should communicate in a friendly and informal way.",
    'concise': "Your answers must be as short and to the point as possible.",
    'detailed': "Provide detailed and comprehensive answers, explaining all aspects.",
}


async def get_system_instruction_text(user_id: int) -> Optional[str]:
    """Build the effective system instruction text for the user.

    Preference order:
    1. Explicit persona prompt
    2. Fallback style prompt
    3. No instruction
    """
    lang_code = await db_manager.get_user_language(user_id)

    persona_id = await db_manager.get_user_persona(user_id)
    if persona_id != 'default':
        persona_info = BOT_PERSONAS.get(persona_id, BOT_PERSONAS['default'])
        prompt_key = f"prompt_{lang_code}"
        persona_prompt = persona_info.get(prompt_key, persona_info.get('prompt_ru', ''))
        return persona_prompt.strip() if persona_prompt else None

    style_id = await db_manager.get_user_bot_style(user_id)
    style_prompt = _STYLE_PROMPTS.get(style_id, "") if style_id != 'default' else ""
    return style_prompt.strip() if style_prompt else None
