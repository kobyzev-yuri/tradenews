"""Загрузка и проверка JSON-фикстур статей (совместимо с nyse serialize_news_article)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_KEYS = frozenset({"ticker", "title", "timestamp", "provider_id"})


def load_articles_fixture(path: Path | str) -> list[dict[str, Any]]:
    """Читает JSON-массив статей; минимальная проверка полей."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{p}: expected JSON array")
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{p}[{i}]: expected object")
        missing = REQUIRED_KEYS - item.keys()
        if missing:
            raise ValueError(f"{p}[{i}]: missing keys {missing}")
    return raw
