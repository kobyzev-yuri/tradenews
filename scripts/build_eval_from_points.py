#!/usr/bin/env python3
"""
Сборка EvaluationRow JSONL из DatasetPoint + несколько моделей (Ollama и/или OpenAI) + yfinance val.

Пример (только Ollama, как раньше):
  PYTHONPATH=. python scripts/build_eval_from_points.py datasets/points/example_mu.jsonl \\
    --models llama3.2:3b qwen2.5:7b --out runs/example_eval.jsonl

Сравнение с облаком (префикс ``openai:`` — нужен ``OPENAI_API_KEY``):
  export OPENAI_API_KEY=sk-...
  PYTHONPATH=. python scripts/build_eval_from_points.py datasets/points/example_mu.jsonl \\
    --models llama3.2:3b openai:gpt-5.4-mini --out runs/example_eval.jsonl

Явный префикс ``ollama:`` опционален: ``ollama:qwen2.5:7b`` эквивалентен ``qwen2.5:7b``.

Относительные ``points_jsonl``, ``--articles-base``, ``--out``, ``--progress-json`` считаются от **корня пакета tradenews** (рядом с ``tradenews/``), а не от cwd — ``runs/eval.jsonl`` всегда в ``tradenews/runs/``.

Прогресс: в stderr строки [step/total] и ETA (лучше ``python -u`` или ``PYTHONUNBUFFERED=1`` при перенаправлении в файл).
В --out каждая строка JSONL пишется сразу — ``watch -n2 'wc -l runs/out.jsonl'``.
Опционально ``--progress-json runs/progress.json`` — атомарно обновляется до/после каждого вызова модели
(``status=predict_inflight`` пока идёт вызов модели; смотреть ``watch -n1 cat runs/progress.json``).

Смок без Ollama: ``--stub``. Частичный прогон: ``--max-points N``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.dataset_points import read_dataset_points_jsonl, resolve_articles
from tradenews.io import evaluation_row_jsonl_line
from tradenews.predictors.base import NewsPredictor
from tradenews.predictors.ollama import OllamaNewsPredictor, OllamaNewsPredictorStub
from tradenews.predictors.openai_predictor import OpenAINewsPredictor
from tradenews.schemas import EvaluationRow
from tradenews.valuation import forward_log_returns_from_close


def _make_predictor(spec: str, *, stub: bool) -> NewsPredictor:
    """``openai:MODEL`` → OpenAI API; ``ollama:MODEL`` или просто ``MODEL`` → Ollama."""
    if stub:
        return OllamaNewsPredictorStub(model_id=f"stub:{spec}")
    s = spec.strip()
    low = s.lower()
    if low.startswith("openai:"):
        model = s.split(":", 1)[1].strip()
        if not model:
            raise ValueError(f"Empty model in spec: {spec!r}")
        return OpenAINewsPredictor(model)
    if low.startswith("ollama:"):
        model = s.split(":", 1)[1].strip()
        if not model:
            raise ValueError(f"Empty model in spec: {spec!r}")
        return OllamaNewsPredictor(model)
    return OllamaNewsPredictor(s)


def _resolve_cli_path(p: Path, *, root: Path) -> Path:
    """Относительные пути — от корня пакета tradenews, не от cwd (удобно при запуске из произвольной папки)."""
    p = Path(p)
    return p.resolve() if p.is_absolute() else (root / p).resolve()


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build evaluation JSONL from dataset points + Ollama and/or OpenAI models."
    )
    ap.add_argument("points_jsonl", type=Path, help="JSONL of DatasetPoint")
    ap.add_argument(
        "--articles-base",
        type=Path,
        default=None,
        help="Base dir for articles_fixture_path (default: parent dir of points file)",
    )
    ap.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Model specs: Ollama name or openai:MODEL_ID (e.g. llama3.2:3b openai:gpt-5.4-mini)",
    )
    ap.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    ap.add_argument(
        "--max-points",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N points (smoke test / partial run).",
    )
    ap.add_argument(
        "--stub",
        action="store_true",
        help="Do not call Ollama; neutral bias (checks pipeline + yfinance).",
    )
    ap.add_argument(
        "--progress-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Rewrite this file atomically with step/model/ticker and status (predict_inflight | row_done | finished).",
    )
    args = ap.parse_args()

    points_path = _resolve_cli_path(args.points_jsonl, root=_ROOT)
    base = (
        _resolve_cli_path(args.articles_base, root=_ROOT)
        if args.articles_base
        else points_path.parent
    )

    points = read_dataset_points_jsonl(points_path)
    if args.max_points is not None:
        points = points[: max(0, args.max_points)]

    out_path = _resolve_cli_path(args.out, root=_ROOT)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_models = len(args.models)
    total_steps = len(points) * n_models
    rows_written = 0
    t_run0 = time.perf_counter()
    progress_path = (
        _resolve_cli_path(args.progress_json, root=_ROOT) if args.progress_json else None
    )

    def _progress(payload: dict) -> None:
        if progress_path is not None:
            _atomic_write_json(progress_path, payload)

    _progress(
        {
            "updated_unix": time.time(),
            "status": "started",
            "rows_completed": 0,
            "total_steps": total_steps,
            "points_total": len(points),
            "stub": args.stub,
            "out": str(out_path),
        }
    )

    with out_path.open("w", encoding="utf-8") as out_f:
        for pi, pt in enumerate(points, start=1):
            arts = resolve_articles(pt, articles_base=base)
            fwd = forward_log_returns_from_close(pt.ticker, pt.decision_ts_utc)

            extra: dict = {}
            if pt.event_tag is not None:
                extra["event_tag"] = pt.event_tag
            if pt.notes is not None:
                extra["notes"] = pt.notes
            if pt.tech_bias is not None:
                extra["tech_bias"] = pt.tech_bias

            for model_name in args.models:
                pred = _make_predictor(model_name, stub=args.stub)
                step_inflight = rows_written + 1
                _progress(
                    {
                        "updated_unix": time.time(),
                        "status": "predict_inflight",
                        "rows_completed": rows_written,
                        "step_inflight": step_inflight,
                        "total_steps": total_steps,
                        "point_index": pi,
                        "points_total": len(points),
                        "model": model_name,
                        "ticker": pt.ticker,
                        "stub": args.stub,
                    }
                )
                t0 = time.perf_counter()
                out = pred.predict(pt.ticker, pt.decision_ts_utc, articles_snapshot=arts)
                predict_sec = time.perf_counter() - t0
                row = EvaluationRow(
                    ticker=pt.ticker,
                    decision_ts_utc=pt.decision_ts_utc,
                    model_id=pred.model_id,
                    bias_predict=out.bias,
                    confidence_predict=out.confidence,
                    forward_log_return_1d=fwd.get("forward_log_return_1d"),
                    forward_log_return_3d=fwd.get("forward_log_return_3d"),
                    forward_log_return_5d=fwd.get("forward_log_return_5d"),
                    llm_mode=(
                        "ollama_stub"
                        if args.stub
                        else (
                            "openai_full"
                            if pred.model_id.startswith("openai:")
                            else "ollama_full"
                        )
                    ),
                    extra=extra,
                )
                out_f.write(evaluation_row_jsonl_line(row))
                out_f.flush()
                rows_written += 1
                elapsed = time.perf_counter() - t_run0
                rem = total_steps - rows_written
                eta_s = (elapsed / rows_written) * rem if rows_written else 0.0
                print(
                    f"[{rows_written}/{total_steps}] point {pi}/{len(points)} "
                    f"model={model_name} ticker={pt.ticker} "
                    f"predict={predict_sec:.2f}s elapsed={elapsed:.1f}s eta~{eta_s:.0f}s",
                    file=sys.stderr,
                    flush=True,
                )
                _progress(
                    {
                        "updated_unix": time.time(),
                        "status": "row_done",
                        "rows_completed": rows_written,
                        "total_steps": total_steps,
                        "point_index": pi,
                        "points_total": len(points),
                        "model": model_name,
                        "ticker": pt.ticker,
                        "last_predict_sec": round(predict_sec, 3),
                        "elapsed_sec": round(elapsed, 3),
                        "eta_sec": round(eta_s, 1),
                        "stub": args.stub,
                    }
                )

    total_sec = time.perf_counter() - t_run0
    print(
        f"Done: {rows_written} rows -> {out_path} (total {total_sec:.1f}s, stub={args.stub})",
        file=sys.stderr,
        flush=True,
    )
    _progress(
        {
            "updated_unix": time.time(),
            "status": "finished",
            "rows_completed": rows_written,
            "total_steps": total_steps,
            "total_sec": round(total_sec, 3),
            "stub": args.stub,
            "out": str(out_path),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
