#!/usr/bin/env python3
"""
Один прогон OpenAI-совместимого API по JSON-фикстуре статей.

  export OPENAI_API_KEY=...
  PYTHONPATH=. python scripts/run_openai_predict_fixture.py \\
    fixtures/articles/minimal_example.json MU
  PYTHONPATH=. python scripts/run_openai_predict_fixture.py -v fixtures/articles/minimal_example.json MU

Третий аргумент — явное имя модели. Иначе: TRADENEWS_OPENAI_MODEL, затем OPENAI_MODEL, иначе gpt-5.4-mini.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.article_fixture import load_articles_fixture
from tradenews.predictors.openai_predictor import OpenAINewsPredictor


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Добавить в JSON поле items (разбор ответа модели) для отладки bias/confidence",
    )
    ap.add_argument("fixture", type=Path, help="JSON array of articles")
    ap.add_argument("ticker", help="Target ticker, e.g. MU")
    ap.add_argument(
        "model",
        nargs="?",
        default="",
        help="OpenAI model id (default: env TRADENEWS_OPENAI_MODEL / OPENAI_MODEL / gpt-5.4-mini)",
    )
    args = ap.parse_args()

    if not (
        (os.environ.get("OPENAI_API_KEY") or "").strip()
        or (os.environ.get("OPENAI_GPT_KEY") or "").strip()
    ):
        print("Задайте OPENAI_API_KEY или OPENAI_GPT_KEY", file=sys.stderr)
        return 2

    arts = load_articles_fixture(args.fixture)
    cli_model = (args.model or "").strip()
    pred = OpenAINewsPredictor(cli_model or None)
    out = pred.predict(
        args.ticker.upper(),
        datetime.now(timezone.utc),
        articles_snapshot=arts,
    )
    payload: dict = {
        "model_id": pred.model_id,
        "bias": out.bias,
        "confidence": out.confidence,
        "raw_keys": list((out.raw or {}).keys()),
    }
    if args.verbose:
        payload["items"] = (out.raw or {}).get("items")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
