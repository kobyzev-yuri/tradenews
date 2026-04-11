#!/usr/bin/env python3
"""
Бенчмарк моделей новостного сигнала: метрики по EvaluationRow JSONL (все горизонты 1d/3d/5d).

Режим A — только отчёт по готовому eval:
  PYTHONPATH=. python scripts/run_model_benchmark.py runs/eval.jsonl --report-json runs/benchmark.json

Режим B — сначала сборка eval, затем отчёт:
  PYTHONPATH=. python scripts/run_model_benchmark.py --build datasets/points/example_mu.jsonl \\
    --articles-base datasets --models llama3.2:3b openai:gpt-5.4-mini \\
    --out-jsonl runs/bench.jsonl --report-json runs/benchmark.json

С ключами из lse/config.env:
  ./scripts/with_lse_config_env.sh bash -c \\
    'PYTHONPATH=. python scripts/run_model_benchmark.py --build ... --out-jsonl runs/bench.jsonl'
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.benchmark_report import (
    DEFAULT_HORIZONS,
    benchmark_report_from_eval_jsonl,
    print_benchmark_narrative,
)


def _run_build_eval(
    *,
    points: Path,
    out_jsonl: Path,
    models: list[str],
    articles_base: Path | None,
    stub: bool,
    max_points: int | None,
    progress_json: Path | None,
) -> None:
    cmd = [
        sys.executable,
        "-u",
        str(_ROOT / "scripts/build_eval_from_points.py"),
        str(points),
        "--out",
        str(out_jsonl),
        "--models",
        *models,
    ]
    if articles_base is not None:
        cmd.extend(["--articles-base", str(articles_base)])
    if stub:
        cmd.append("--stub")
    if max_points is not None:
        cmd.extend(["--max-points", str(max_points)])
    if progress_json is not None:
        cmd.extend(["--progress-json", str(progress_json)])
    env = {**os.environ, "PYTHONPATH": str(_ROOT), "PYTHONUNBUFFERED": "1"}
    subprocess.run(cmd, cwd=str(_ROOT), env=env, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Multi-horizon benchmark report from EvaluationRow JSONL (optionally build eval first)."
    )
    ap.add_argument(
        "eval_jsonl",
        nargs="?",
        default=None,
        help="Готовый JSONL со строками EvaluationRow",
    )
    ap.add_argument(
        "--build",
        type=Path,
        metavar="POINTS_JSONL",
        default=None,
        help="Перед отчётом вызвать build_eval_from_points.py для этого файла точек",
    )
    ap.add_argument("--articles-base", type=Path, default=None, help="База для articles_fixture_path")
    ap.add_argument("--models", nargs="+", default=None, help="С --build: спецификации моделей")
    ap.add_argument(
        "--out-jsonl",
        type=Path,
        default=None,
        help="С --build: куда писать eval (и откуда читать метрики)",
    )
    ap.add_argument("--stub", action="store_true", help="С --build: без реальных LLM")
    ap.add_argument("--max-points", type=int, default=None, metavar="N", help="С --build: лимит точек")
    ap.add_argument("--progress-json", type=Path, default=None, help="С --build: прогресс для watch")
    ap.add_argument("--report-json", type=Path, default=None, help="Записать полный отчёт в JSON")
    ap.add_argument(
        "--min-abs-predict",
        type=float,
        default=0.05,
        help="Порог |bias| для колонки hit_rate (как в run_compare)",
    )
    ap.add_argument(
        "--horizons",
        nargs="+",
        default=list(DEFAULT_HORIZONS),
        metavar="COL",
        help="Колонки forward log-return (по умолчанию 1d 3d 5d)",
    )
    ap.add_argument("-q", "--quiet", action="store_true", help="Не печатать таблицы в stdout")
    args = ap.parse_args()

    eval_path: Path | None = None
    if args.build is not None:
        if not args.models:
            ap.error("--build требует --models")
        if args.out_jsonl is None:
            ap.error("--build требует --out-jsonl")
        out_resolved = args.out_jsonl if args.out_jsonl.is_absolute() else (_ROOT / args.out_jsonl)
        points_resolved = args.build if args.build.is_absolute() else (_ROOT / args.build)
        _run_build_eval(
            points=points_resolved,
            out_jsonl=out_resolved,
            models=list(args.models),
            articles_base=(
                (args.articles_base if args.articles_base.is_absolute() else _ROOT / args.articles_base)
                if args.articles_base is not None
                else None
            ),
            stub=args.stub,
            max_points=args.max_points,
            progress_json=(
                (args.progress_json if args.progress_json.is_absolute() else _ROOT / args.progress_json)
                if args.progress_json is not None
                else None
            ),
        )
        eval_path = out_resolved
    elif args.eval_jsonl is not None:
        p = Path(args.eval_jsonl)
        eval_path = p if p.is_absolute() else (_ROOT / p)
    else:
        ap.error("Укажите путь к eval JSONL или --build POINTS --models ... --out-jsonl ...")

    assert eval_path is not None
    if not eval_path.is_file():
        print(f"Нет файла {eval_path}", file=sys.stderr)
        return 1

    horizons = tuple(args.horizons)
    report = benchmark_report_from_eval_jsonl(
        eval_path,
        horizons=horizons,
        min_abs_predict=args.min_abs_predict,
    )
    if not args.quiet:
        print_benchmark_narrative(report)
    if args.report_json is not None:
        rp = args.report_json if args.report_json.is_absolute() else (_ROOT / args.report_json)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not args.quiet:
            print(f"\n# report written: {rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
