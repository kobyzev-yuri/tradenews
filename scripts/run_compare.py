#!/usr/bin/env python3
"""Печать сводки метрик по JSONL со строками EvaluationRow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# запуск из корня tradenews: python scripts/run_compare.py runs/eval.jsonl
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.compare import print_compare_report


def main() -> int:
    p = argparse.ArgumentParser(description="Summarize news predict vs forward returns by model_id.")
    p.add_argument("jsonl", type=Path, help="Path to JSONL (one EvaluationRow per line)")
    p.add_argument(
        "--return-col",
        default="forward_log_return_1d",
        help="Column for realized return (default: forward_log_return_1d)",
    )
    args = p.parse_args()
    print_compare_report(args.jsonl, return_col=args.return_col)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
