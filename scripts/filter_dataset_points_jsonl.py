#!/usr/bin/env python3
"""
Фильтр JSONL DatasetPoint: убрать псевдо-тикеры (макро/кэш) для оценки vs yfinance.

Пример:
  PYTHONPATH=. python scripts/filter_dataset_points_jsonl.py \\
    datasets/points/lse_kb_per_row.jsonl \\
    --out datasets/points/lse_kb_per_row_equities.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.dataset_points import read_dataset_points_jsonl
from tradenews.lse_kb_converter import write_dataset_points_jsonl


def _resolve_cli_path(p: Path, *, root: Path) -> Path:
    p = Path(p)
    return p.resolve() if p.is_absolute() else (root / p).resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description="Filter DatasetPoint JSONL by ticker denylist.")
    ap.add_argument("points_jsonl", type=Path, help="Input JSONL")
    ap.add_argument("--out", type=Path, required=True, help="Output JSONL")
    ap.add_argument(
        "--exclude-tickers",
        default="US_MACRO,MACRO,CASH",
        help="Comma-separated tickers to drop (default: LSE-style pseudo tickers)",
    )
    args = ap.parse_args()

    inp = _resolve_cli_path(args.points_jsonl, root=_ROOT)
    out = _resolve_cli_path(args.out, root=_ROOT)
    ex = {t.strip().upper() for t in args.exclude_tickers.split(",") if t.strip()}

    points = read_dataset_points_jsonl(inp)
    kept = [p for p in points if p.ticker.upper() not in ex]
    dropped = len(points) - len(kept)

    n = write_dataset_points_jsonl(iter(kept), out)
    print(
        f"filter_dataset_points: in={len(points)} out={n} dropped={dropped} exclude={sorted(ex)} -> {out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
