from pathlib import Path

import pytest

from tradenews.article_fixture import load_articles_fixture

_FIX = Path(__file__).resolve().parent.parent / "fixtures" / "articles" / "minimal_example.json"


def test_load_minimal_fixture():
    arts = load_articles_fixture(_FIX)
    assert len(arts) == 2
    assert arts[0]["ticker"] == "MU"
    assert arts[0]["provider_id"] == "fixture"


def test_load_missing_file():
    with pytest.raises(OSError):
        load_articles_fixture("/nonexistent/path.json")
