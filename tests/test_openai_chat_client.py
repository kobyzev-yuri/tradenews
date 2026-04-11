"""openai_chat_client: выбор max_tokens vs max_completion_tokens."""

from __future__ import annotations

import os

import pytest

from tradenews.openai_chat_client import _completion_tokens_field


@pytest.mark.parametrize(
    "model,expected",
    [
        ("gpt-5.4-mini", "max_completion_tokens"),
        ("GPT-5", "max_completion_tokens"),
        ("gpt-4.1-mini", "max_completion_tokens"),
        ("o3-mini", "max_completion_tokens"),
        ("gpt-4o-mini", "max_tokens"),
        ("gpt-4o", "max_tokens"),
    ],
)
def test_completion_tokens_field_by_model(model: str, expected: str) -> None:
    old = os.environ.pop("TRADENEWS_OPENAI_MAX_TOKENS_PARAM", None)
    try:
        assert _completion_tokens_field(model) == expected
    finally:
        if old is not None:
            os.environ["TRADENEWS_OPENAI_MAX_TOKENS_PARAM"] = old


def test_completion_tokens_field_env_override() -> None:
    os.environ["TRADENEWS_OPENAI_MAX_TOKENS_PARAM"] = "max_tokens"
    try:
        assert _completion_tokens_field("gpt-5.4-mini") == "max_tokens"
    finally:
        os.environ.pop("TRADENEWS_OPENAI_MAX_TOKENS_PARAM", None)
