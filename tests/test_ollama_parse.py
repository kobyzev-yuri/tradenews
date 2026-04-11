import json

from tradenews.ollama_client import (
    _parse_keep_alive,
    parse_news_signal_response,
    strip_json_fence,
)


def test_strip_fence():
    raw = "```json\n{\"items\": []}\n```"
    assert '"items"' in strip_json_fence(raw)


def test_parse_keep_alive():
    assert _parse_keep_alive("30m") == "30m"
    assert _parse_keep_alive("600") == 600
    assert _parse_keep_alive("-1") == -1


def test_parse_items():
    raw = json.dumps(
        {
            "items": [
                {
                    "article_index": 1,
                    "sentiment": 0.5,
                    "impact_strength": "moderate",
                    "relevance": "related",
                    "surprise": "minor",
                    "time_horizon": "1-3d",
                    "confidence": 0.8,
                }
            ]
        }
    )
    items = parse_news_signal_response(raw)
    assert len(items) == 1
    assert items[0]["sentiment"] == 0.5
