import importlib

import pytest


def test_parse_chat_completions_response_extracts_text_and_usage():
    parser = importlib.import_module("services.openai_response_parser")
    parser = importlib.reload(parser)

    parsed = parser.parse_chat_completions_response(
        {
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
            "choices": [{"message": {"content": "hello world"}}],
        }
    )

    assert parsed == {
        "response_text": "hello world",
        "sources": [],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }


def test_parse_chat_completions_response_supports_list_content():
    parser = importlib.import_module("services.openai_response_parser")
    parser = importlib.reload(parser)

    parsed = parser.parse_chat_completions_response(
        {
            "choices": [{"message": {"content": [{"text": "hello"}, {"text": " world"}]}}],
        }
    )

    assert parsed["response_text"] == "hello world"


def test_parse_chat_completions_response_raises_on_invalid_shape():
    parser = importlib.import_module("services.openai_response_parser")
    parser = importlib.reload(parser)

    with pytest.raises(parser.OpenAIAPIError):
        parser.parse_chat_completions_response({})
