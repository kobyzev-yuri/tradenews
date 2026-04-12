#!/usr/bin/env python3
"""
Один прогон Ollama по JSON-фикстуре статей (нужен ollama serve).

  PYTHONPATH=. python scripts/run_ollama_predict_fixture.py \
    fixtures/articles/minimal_example.json MU llama3.2:3b
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.article_fixture import load_articles_fixture
from tradenews.predictors.ollama import OllamaNewsPredictor


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", type=Path, help="JSON array of articles")
    ap.add_argument("ticker", help="Target ticker, e.g. MU")
    ap.add_argument("model", help="Ollama model name, e.g. llama3.2:3b")
    args = ap.parse_args()

    arts = load_articles_fixture(args.fixture)
    pred = OllamaNewsPredictor(args.model)
    out = pred.predict(
        args.ticker.upper(),
        datetime.now(timezone.utc),
        articles_snapshot=arts,
    )
    print(
        json.dumps(
            {
                "model_id": pred.model_id,
                "bias": out.bias,
                "confidence": out.confidence,
                "raw_keys": list((out.raw or {}).keys()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
