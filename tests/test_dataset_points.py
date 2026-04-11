from datetime import datetime, timezone
from pathlib import Path

from tradenews.dataset_points import read_dataset_points_jsonl, resolve_articles
from tradenews.schemas import DatasetPoint


def test_resolve_fixture_path():
    root = Path(__file__).resolve().parent.parent
    pt = DatasetPoint(
        ticker="MU",
        decision_ts_utc=datetime(2026, 3, 10, 16, 0, tzinfo=timezone.utc),
        articles_fixture_path="articles/minimal_example.json",
    )
    arts = resolve_articles(pt, articles_base=root / "datasets")
    assert len(arts) == 2
    assert arts[0]["ticker"] == "MU"


def test_read_example_jsonl():
    root = Path(__file__).resolve().parent.parent
    pts = read_dataset_points_jsonl(root / "datasets" / "points" / "example_mu.jsonl")
    assert len(pts) == 1
    assert pts[0].event_tag == "fixture_smoke"
