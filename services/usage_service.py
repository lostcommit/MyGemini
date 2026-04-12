from typing import Dict, Optional

from config.settings import TOKEN_PRICING
from .llm_backends import GEMINI_BACKEND, OPENAI_BACKEND, get_backend_display_name


OPENAI_TOKEN_PRICING: Dict[str, Dict[str, float]] = {}


async def get_usage_context(settings_service, user_id: int) -> Dict[str, Optional[str]]:
    backend = await settings_service.get_user_backend(user_id)
    model_name = await settings_service.get_effective_model(user_id)
    return {
        "backend": backend,
        "backend_name": get_backend_display_name(backend),
        "model_name": model_name,
    }


def get_pricing_for_backend_model(backend: str, model_name: Optional[str]) -> Optional[Dict[str, float]]:
    if backend == GEMINI_BACKEND:
        if model_name and model_name in TOKEN_PRICING:
            return TOKEN_PRICING[model_name]
        return TOKEN_PRICING.get("default")
    if backend == OPENAI_BACKEND:
        if model_name:
            return OPENAI_TOKEN_PRICING.get(model_name)
        return None
    return None


def calculate_usage_cost(usage_data: Dict[str, int], pricing: Optional[Dict[str, float]]) -> Optional[float]:
    if not pricing:
        return None
    input_cost = (usage_data["prompt_tokens"] / 1_000_000) * pricing["input_usd_per_million"]
    output_cost = (usage_data["completion_tokens"] / 1_000_000) * pricing["output_usd_per_million"]
    return input_cost + output_cost
