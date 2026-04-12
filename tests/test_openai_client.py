from services.openai_client import OpenAIAPIError


def test_openai_invalid_api_key_maps_to_localized_error_key():
    err = OpenAIAPIError(
        "Incorrect API key provided",
        details={"error": {"message": "Incorrect API key provided"}},
    )

    assert err.error_key == "openai_error_api_key_invalid"


def test_openai_timeout_maps_to_localized_error_key():
    err = OpenAIAPIError(
        "OpenAI server timeout",
        details={"error": {"message": "service_timeout"}},
    )

    assert err.error_key == "openai_error_timeout"
