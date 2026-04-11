#!/usr/bin/env python3
"""
Однократная выгрузка новостей тем же NewsSource, что nyse бот/CLI → JSON-фикстура.

Требуется:
  - NYSE_PROJECT_ROOT (корень репозитория nyse) в PYTHONPATH или переменной окружения
  - при необходимости config.env в корне nyse для ключей API

Пример:
  export NYSE_PROJECT_ROOT=/path/to/nyse
  PYTHONPATH=. python scripts/fetch_nyse_articles_fixture.py MU --out ../fixtures/articles/mu_live.json
"""

from __future__ import annotations

import argparse
import json
import sys
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
    ap = argparse.ArgumentParser(description="Fetch news via nyse NewsSource and save JSON fixture.")
    ap.add_argument("ticker", help="Ticker, e.g. MU")
    ap.add_argument("--out", type=Path, required=True, help="Output JSON path (array of articles)")
    ap.add_argument("--lookback-hours", type=int, default=48)
    ap.add_argument("--max-per-ticker", type=int, default=10)
    args = ap.parse_args()

    _ensure_nyse_path()

    import config_loader
    from domain import Ticker
    from pipeline.news_cache import serialize_news_article
    from sources.news import Source as NewsSource

    config_loader.load_config_env()
    t = Ticker(args.ticker.strip().upper())
    src = NewsSource(max_per_ticker=args.max_per_ticker, lookback_hours=args.lookback_hours)
    articles = src.get_articles([t])
    articles = [a for a in articles if a.ticker == t]
    payload = [serialize_news_article(a) for a in articles]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload)} articles to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
