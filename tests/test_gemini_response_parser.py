import importlib

import pytest


def test_parse_generate_content_response_extracts_text_sources_and_usage():
    parser = importlib.import_module("services.gemini_response_parser")
    parser = importlib.reload(parser)

    response_json = {
        "usageMetadata": {
            "promptTokenCount": 11,
            "candidatesTokenCount": 7,
            "totalTokenCount": 18,
        },
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Hello"},
                        {"text": " world"},
                    ]
                },
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"uri": "https://example.com/a", "title": "A"}},
                        {"web": {"uri": "https://example.com/a", "title": "A"}},
                        {"web": {"uri": "https://example.com/b", "title": "B"}},
                    ]
                },
            }
        ],
    }

    parsed = parser.parse_generate_content_response(response_json)

    assert parsed["response_text"] == "Hello world"
    assert parsed["sources"] == [
        {"uri": "https://example.com/a", "title": "A"},
        {"uri": "https://example.com/b", "title": "B"},
    ]
    assert parsed["usage"] == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }


def test_parse_generate_content_response_supports_grounding_attributions():
    parser = importlib.import_module("services.gemini_response_parser")
    parser = importlib.reload(parser)

    response_json = {
        "candidates": [
            {
                "content": {"parts": [{"text": "ok"}]},
                "groundingMetadata": {
                    "groundingAttributions": [
                        {"web": {"uri": "https://example.com", "title": "Example"}}
                    ]
                },
            }
        ]
    }

    parsed = parser.parse_generate_content_response(response_json)
    assert parsed["sources"] == [{"uri": "https://example.com", "title": "Example"}]


def test_parse_generate_content_response_raises_on_safety_block():
    parser = importlib.import_module("services.gemini_response_parser")
    parser = importlib.reload(parser)

    with pytest.raises(parser.GeminiAPIError):
        parser.parse_generate_content_response(
            {
                "candidates": [
                    {
                        "finishReason": "SAFETY",
                        "content": {"parts": [{"text": "hidden"}]},
                    }
                ]
            }
        )


def test_parse_simple_text_response_raises_on_invalid_shape():
    parser = importlib.import_module("services.gemini_response_parser")
    parser = importlib.reload(parser)

    with pytest.raises(parser.GeminiAPIError):
        parser.parse_simple_text_response({"candidates": []})
