from tradenews.signal_aggregate import aggregate_llm_items

# Тот же пример, что ``python -m pipeline.news.news_signal_aggregator`` в nyse (__main__)
_NYSE_AGG_DEMO_ITEMS = [
    {
        "article_index": 1,
        "sentiment": 0.5,
        "impact_strength": "high",
        "relevance": "primary",
        "surprise": "significant",
        "time_horizon": "1-3d",
        "confidence": 0.8,
    },
    {
        "article_index": 2,
        "sentiment": -0.3,
        "impact_strength": "moderate",
        "relevance": "related",
        "surprise": "minor",
        "time_horizon": "intraday",
        "confidence": 0.5,
    },
]


def test_aggregate_matches_nyse_demo_main() -> None:
    bias, conf = aggregate_llm_items(_NYSE_AGG_DEMO_ITEMS)
    assert abs(bias - 0.3426) < 0.0002
    assert abs(conf - 0.7410) < 0.0002


def test_sentiment_clipped_to_unit_interval() -> None:
    """Как границы Pydantic у nyse ``NewsSignalLLMItem.sentiment`` (−1…1)."""
    items = [
        {
            "article_index": 1,
            "sentiment": 2.0,
            "impact_strength": "high",
            "relevance": "primary",
            "time_horizon": "1-3d",
            "confidence": 1.0,
        }
    ]
    bias, _ = aggregate_llm_items(items)
    assert abs(bias - 1.0) < 1e-9


def test_aggregate_two_items():
    items = [
        {
            "article_index": 1,
            "sentiment": 1.0,
            "impact_strength": "high",
            "relevance": "primary",
            "time_horizon": "1-3d",
            "confidence": 1.0,
        },
        {
            "article_index": 2,
            "sentiment": -1.0,
            "impact_strength": "high",
            "relevance": "primary",
            "time_horizon": "1-3d",
            "confidence": 1.0,
        },
    ]
    bias, conf = aggregate_llm_items(items)
    assert abs(bias) < 1e-9
    assert abs(conf - 1.0) < 1e-9
