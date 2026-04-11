from datetime import datetime, timezone

import pandas as pd

from tradenews.lse_kb_converter import (
    iter_dataset_points_from_kb,
    kb_row_to_article,
    parse_ts_utc,
)
from tradenews.schemas import DatasetPoint


def test_parse_ts_naive_utc():
    assert parse_ts_utc("2026-03-10 16:00:00").isoformat() == "2026-03-10T16:00:00+00:00"


def test_kb_row_to_article():
    row = pd.Series(
        {
            "ts": "2026-03-10 16:00:00",
            "ticker": "mu",
            "source": "Reuters",
            "content": "Micron beats estimates\n\nDetails here.",
            "sentiment_score": 0.75,
            "link": "https://example.com/a",
        }
    )
    a = kb_row_to_article(row)
    assert a["ticker"] == "MU"
    assert "Micron" in a["title"]
    assert a["summary"] and "Details" in a["summary"]
    assert a["cheap_sentiment"] is not None
    assert abs(a["cheap_sentiment"] - 0.5) < 0.01  # (0.75-0.5)*2
    assert a["provider_id"] == "lse_kb"


def test_per_row_iterator():
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "ts": "2026-03-10 10:00:00",
                "ticker": "MU",
                "source": "S",
                "content": "Title A\nbody",
                "sentiment_score": 0.5,
                "event_type": "NEWS",
                "link": "",
            },
            {
                "id": 2,
                "ts": "2026-03-11 11:00:00",
                "ticker": "QQQ",
                "source": "S",
                "content": "Title B",
                "sentiment_score": None,
                "event_type": None,
                "link": None,
            },
        ]
    )
    pts = list(iter_dataset_points_from_kb(df, mode="per_row"))
    assert len(pts) == 2
    assert isinstance(pts[0], DatasetPoint)
    assert pts[0].ticker == "MU"
    assert len(pts[0].articles_snapshot or []) == 1


def test_daily_groups_by_ticker_day():
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "ts": "2026-03-10 10:00:00",
                "ticker": "MU",
                "source": "S",
                "content": "A\nx",
                "event_type": "NEWS",
            },
            {
                "id": 2,
                "ts": "2026-03-10 18:00:00",
                "ticker": "MU",
                "source": "S",
                "content": "B",
                "event_type": "NEWS",
            },
        ]
    )
    pts = list(iter_dataset_points_from_kb(df, mode="daily"))
    assert len(pts) == 1
    assert pts[0].ticker == "MU"
    assert len(pts[0].articles_snapshot or []) == 2
    assert pts[0].decision_ts_utc == datetime(2026, 3, 10, 18, 0, tzinfo=timezone.utc)
