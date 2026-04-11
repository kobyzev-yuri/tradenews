#!/usr/bin/env python3
"""
CSV knowledge_base (LSE GCP dump) → JSONL DatasetPoint для tradenews.

Пример:
  PYTHONPATH=. python scripts/lse_csv_to_dataset_points.py \\
    --kb datasets/lse_gcp_dump/knowledge_base_last90d_*.csv \\
    --out datasets/points/lse_kb_per_row.jsonl \\
    --mode per_row --max-points 200

Режимы:
  per_row — одна строка KB → одна точка (одна статья), decision_ts = ts новости.
  daily   — группировка (ticker, день UTC), decision_ts = последний ts в группе, все статьи в snapshot.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.lse_kb_converter import (
    iter_dataset_points_from_kb,
    load_kb_csv,
    write_dataset_points_jsonl,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="LSE knowledge_base CSV → DatasetPoint JSONL")
    ap.add_argument("--kb", type=Path, required=True, help="Path to knowledge_base CSV")
    ap.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    ap.add_argument(
        "--mode",
        choices=("per_row", "daily"),
        default="per_row",
        help="per_row: one point per KB row; daily: group by ticker and UTC date",
    )
    ap.add_argument(
        "--tickers",
        default="",
        help="Comma-separated tickers filter (empty = all)",
    )
    ap.add_argument(
        "--exclude-tickers",
        default="US_MACRO,MACRO,CASH",
        help="Comma-separated tickers to drop from CSV (default: LSE macro pseudo-tickers)",
    )
    ap.add_argument("--max-points", type=int, default=0, help="Max DatasetPoint lines (0 = no limit)")
    args = ap.parse_args()

    tickers: set[str] | None = None
    if args.tickers.strip():
        tickers = {t.strip().upper() for t in args.tickers.split(",") if t.strip()}

    df = load_kb_csv(args.kb)
    if args.exclude_tickers.strip():
        ex = {t.strip().upper() for t in args.exclude_tickers.split(",") if t.strip()}
        if ex and "ticker" in df.columns:
            df = df[~df["ticker"].str.upper().isin(ex)]
    max_pts = args.max_points if args.max_points > 0 else None
    it = iter_dataset_points_from_kb(
        df,
        mode=args.mode,
        tickers=tickers,
        max_points=max_pts,
    )
    n = write_dataset_points_jsonl(it, args.out)
    print(f"Wrote {n} DatasetPoint lines to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
