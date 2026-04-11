"""OpenAINewsPredictor: мок HTTP, без реального API."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from tradenews.predictors.openai_predictor import OpenAINewsPredictor


_JSON = (
    '{"items":['
    '{"article_index":1,"sentiment":0.5,"impact_strength":"moderate",'
    '"relevance":"primary","surprise":"none","time_horizon":"1-3d","confidence":0.8}'
    "]}"
)


@patch("tradenews.predictors.openai_predictor.openai_chat_completions", return_value=_JSON)
def test_openai_predictor_returns_bias(mock_chat: object) -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    arts = [
        {
            "title": "Test",
            "summary": "Good news for MU",
            "timestamp": "2025-01-01T12:00:00Z",
            "publisher": "test",
        }
    ]
    pred = OpenAINewsPredictor("gpt-test-model")
    assert pred.model_id == "openai:gpt-test-model"
    out = pred.predict("MU", datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc), articles_snapshot=arts)
    assert out.bias is not None
    assert -1.0 <= out.bias <= 1.0
    mock_chat.assert_called_once()


def test_openai_predictor_requires_key() -> None:
    old = os.environ.pop("OPENAI_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAINewsPredictor("gpt-x")
    finally:
        if old is not None:
            os.environ["OPENAI_API_KEY"] = old
