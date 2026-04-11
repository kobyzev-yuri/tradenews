#!/usr/bin/env python3
"""
Снимок новостей по списку тикеров (nyse NewsSource) + дописывание строк DatasetPoint в JSONL.

Требуется NYSE_PROJECT_ROOT и при необходимости config.env в корне nyse.

Пример:
  export NYSE_PROJECT_ROOT=~/projects/lse/nyse
  PYTHONPATH=. python scripts/snapshot_live_dataset.py \\
    --tickers MU,NBIS,QQQ --articles-dir datasets/articles \\
    --append-points datasets/points/live_accum.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _ensure_nyse_path() -> Path:
    import os

    root = os.environ.get("NYSE_PROJECT_ROOT", "").strip()
    if not root:
        raise SystemExit("Set NYSE_PROJECT_ROOT to the nyse repository root.")
    p = Path(root).resolve()
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Live news snapshot per ticker + append DatasetPoint JSONL.")
    ap.add_argument(
        "--tickers",
        required=True,
        help="Comma-separated tickers, e.g. MU,NBIS,QQQ",
    )
    ap.add_argument("--articles-dir", type=Path, required=True, help="Where to write article JSON files")
    ap.add_argument(
        "--append-points",
        type=Path,
        required=True,
        help="JSONL file to append one DatasetPoint line per ticker",
    )
    ap.add_argument("--lookback-hours", type=int, default=48)
    ap.add_argument("--max-per-ticker", type=int, default=10)
    ap.add_argument("--event-tag", default="", help="Optional event_tag on each point")
    ap.add_argument("--notes", default="", help="Optional notes string")
    args = ap.parse_args()

    _ensure_nyse_path()

    import config_loader
    from domain import Ticker
    from pipeline.news_cache import serialize_news_article
    from sources.news import Source as NewsSource

    config_loader.load_config_env()

    now = datetime.now(timezone.utc)
    ts_slug = now.strftime("%Y%m%dT%H%M%SZ")
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        raise SystemExit("No tickers")

    args.articles_dir.mkdir(parents=True, exist_ok=True)
    args.append_points.parent.mkdir(parents=True, exist_ok=True)

    src = NewsSource(max_per_ticker=args.max_per_ticker, lookback_hours=args.lookback_hours)

    with args.append_points.open("a", encoding="utf-8") as jout:
        for tv in tickers:
            t = Ticker(tv)
            articles = src.get_articles([t])
            articles = [a for a in articles if a.ticker == t]
            payload = [serialize_news_article(a) for a in articles]

            rel_name = f"{tv}_{ts_slug}.json"
            art_path = args.articles_dir / rel_name
            art_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            # Путь в JSONL — относительно родителя каталога articles (ожидается .../datasets/articles → .../datasets)
            ds_root = args.articles_dir.resolve().parent
            fixture_rel = art_path.resolve().relative_to(ds_root).as_posix()

            point: dict = {
                "ticker": tv,
                "decision_ts_utc": now.isoformat(),
                "articles_fixture_path": fixture_rel,
            }
            if args.event_tag:
                point["event_tag"] = args.event_tag
            if args.notes:
                point["notes"] = args.notes

            jout.write(json.dumps(point, ensure_ascii=False) + "\n")
            print(f"{tv}: {len(payload)} articles -> {art_path.name}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
