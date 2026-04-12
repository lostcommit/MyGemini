GEMINI_BACKEND = 'gemini'
OPENAI_BACKEND = 'openai'

SUPPORTED_LLM_BACKENDS = (GEMINI_BACKEND, OPENAI_BACKEND)
BACKEND_DISPLAY_NAMES = {
    GEMINI_BACKEND: 'Google Gemini',
    OPENAI_BACKEND: 'OpenAI',
}


def is_supported_backend(backend: str) -> bool:
    return backend in SUPPORTED_LLM_BACKENDS


def get_backend_display_name(backend: str) -> str:
    return BACKEND_DISPLAY_NAMES.get(backend, backend)
