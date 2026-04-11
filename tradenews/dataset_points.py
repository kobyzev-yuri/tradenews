"""Загрузка точек датасета и разрешение статей (snapshot vs fixture path)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tradenews.article_fixture import load_articles_fixture
from tradenews.schemas import DatasetPoint


def read_dataset_points_jsonl(path: Path | str) -> list[DatasetPoint]:
    p = Path(path)
    out: list[DatasetPoint] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append(DatasetPoint.from_json_dict(json.loads(line)))
    return out


def resolve_articles(
    point: DatasetPoint,
    *,
    articles_base: Path,
) -> list[dict[str, Any]]:
    """
    Возвращает список статей для точки.

    ``articles_base`` — корень для относительных путей ``articles_fixture_path``.
    """
    if point.articles_snapshot is not None:
        return list(point.articles_snapshot)
    if point.articles_fixture_path:
        rel = Path(point.articles_fixture_path)
        if not rel.is_absolute():
            fp = (articles_base / rel).resolve()
        else:
            fp = rel
        return load_articles_fixture(fp)
    raise ValueError(
        f"DatasetPoint for {point.ticker} @ {point.decision_ts_utc}: "
        "need articles_snapshot or articles_fixture_path"
    )
