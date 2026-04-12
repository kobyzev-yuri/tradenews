"""
Сводный бенчмарк по ``EvaluationRow`` JSONL: те же метрики, что ``run_compare.py``,
но сразу по нескольким горизонтам forward return и с машиночитаемым JSON-отчётом.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

import pandas as pd

from tradenews.compare import compare_models_report, evaluation_jsonl_to_dataframe
from tradenews.metrics import pairwise_bias_spearman_table

DEFAULT_HORIZONS = (
    "forward_log_return_1d",
    "forward_log_return_3d",
    "forward_log_return_5d",
)


def _df_to_jsonable(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", double_precision=12))


def build_benchmark_report(
    df: pd.DataFrame,
    *,
    horizons: tuple[str, ...] = DEFAULT_HORIZONS,
    min_abs_predict: float = 0.05,
    eval_path: str | None = None,
    spearman_bootstrap_n: int = 0,
    spearman_perm_n: int = 0,
    random_seed: int = 42,
    include_prediction_agreement: bool = True,
) -> dict[str, Any]:
    """
    Строит отчёт: ``meta`` + ``horizons`` → summary, ranking по Spearman IC, бакеты по моделям.

    В ``meta`` при достаточных колонках: ``prediction_agreement`` — попарный Spearman bias↔bias
    на строках, где есть все модели.
    """
    meta: dict[str, Any] = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "eval_path": eval_path,
        "min_abs_predict": min_abs_predict,
        "spearman_bootstrap_n": spearman_bootstrap_n,
        "spearman_perm_n": spearman_perm_n,
        "random_seed": random_seed,
    }
    if len(df) and "model_id" in df.columns:
        meta["model_ids"] = sorted(df["model_id"].astype(str).unique().tolist())
    else:
        meta["model_ids"] = []

    if include_prediction_agreement and len(df):
        pa = pairwise_bias_spearman_table(df)
        meta["prediction_agreement"] = _df_to_jsonable(pa) if not pa.empty else []
    else:
        meta["prediction_agreement"] = []

    by_horizon: dict[str, Any] = {}
    for col in horizons:
        if col not in df.columns:
            by_horizon[col] = {
                "summary": [],
                "ranking_by_spearman_ic": [],
                "confidence_buckets": None,
                "skipped": "column_missing",
            }
            continue
        summary, buckets = compare_models_report(
            df,
            return_col=col,
            min_abs_predict=min_abs_predict,
            spearman_bootstrap_n=spearman_bootstrap_n,
            spearman_perm_n=spearman_perm_n,
            random_seed=random_seed,
        )
        rank = summary.sort_values("spearman_ic", ascending=False, na_position="last")
        buck_records: list[dict[str, Any]] | None = None
        if buckets is not None and not buckets.empty:
            buck_records = _df_to_jsonable(buckets)
        by_horizon[col] = {
            "summary": _df_to_jsonable(summary),
            "ranking_by_spearman_ic": [
                {
                    "model_id": str(r["model_id"]),
                    "spearman_ic": r["spearman_ic"],
                    "n_with_return": int(r["n_with_return"]),
                }
                for _, r in rank.iterrows()
            ],
            "confidence_buckets": buck_records,
        }
    return {"meta": meta, "horizons": by_horizon}


def benchmark_report_from_eval_jsonl(
    path: Path | str,
    *,
    horizons: tuple[str, ...] = DEFAULT_HORIZONS,
    min_abs_predict: float = 0.05,
    spearman_bootstrap_n: int = 0,
    spearman_perm_n: int = 0,
    random_seed: int = 42,
    include_prediction_agreement: bool = True,
) -> dict[str, Any]:
    p = Path(path)
    df = evaluation_jsonl_to_dataframe(p)
    return build_benchmark_report(
        df,
        horizons=horizons,
        min_abs_predict=min_abs_predict,
        eval_path=str(p.resolve()),
        spearman_bootstrap_n=spearman_bootstrap_n,
        spearman_perm_n=spearman_perm_n,
        random_seed=random_seed,
        include_prediction_agreement=include_prediction_agreement,
    )


def print_benchmark_narrative(report: dict[str, Any], *, file: TextIO | None = None) -> None:
    """Текстовая сводка (как несколько вызовов ``run_compare`` подряд)."""
    out = file or sys.stdout
    meta = report.get("meta") or {}
    print("# tradenews model benchmark", file=out)
    print(f"eval: {meta.get('eval_path')}", file=out)
    print(f"rows: {meta.get('n_rows')}  models: {meta.get('model_ids')}", file=out)
    print(f"generated: {meta.get('generated_utc')}", file=out)
    bsn = meta.get("spearman_bootstrap_n")
    psn = meta.get("spearman_perm_n")
    if bsn or psn:
        print(
            f"uncertainty: bootstrap_n={bsn!r} perm_n={psn!r} seed={meta.get('random_seed')!r}",
            file=out,
        )
    pa = meta.get("prediction_agreement") or []
    if pa:
        print("\n=== prediction agreement (Spearman bias vs bias, joint rows) ===", file=out)
        print(pd.DataFrame(pa).to_string(index=False), file=out)

    for hname, block in (report.get("horizons") or {}).items():
        print(f"\n=== {hname} ===", file=out)
        if block.get("skipped"):
            print(f"(пропуск: {block['skipped']})", file=out)
            continue
        summ = block.get("summary") or []
        if not summ:
            print("(пустая сводка)", file=out)
            continue
        print(pd.DataFrame(summ).to_string(index=False), file=out)
        rank = block.get("ranking_by_spearman_ic") or []
        if rank:
            print("\n# ranking by Spearman IC (NaN last)", file=out)
            for i, r in enumerate(rank, 1):
                print(
                    f"  {i}. {r['model_id']!r}  IC={r['spearman_ic']}  n_with_return={r['n_with_return']}",
                    file=out,
                )
        bucks = block.get("confidence_buckets")
        if bucks:
            print("\n--- confidence buckets (per model) ---", file=out)
            bdf = pd.DataFrame(bucks)
            if "model_id" in bdf.columns:
                for mid, gb in bdf.groupby("model_id", sort=True):
                    print(f"\n{mid}", file=out)
                    print(gb.drop(columns=["model_id"]).to_string(index=False), file=out)
            else:
                print(bdf.to_string(index=False), file=out)

    max_n = 0
    for block in (report.get("horizons") or {}).values():
        for row in block.get("summary") or []:
            max_n = max(max_n, int(row.get("n_with_return") or 0))
    if max_n < 3:
        print(
            "\n-- Пояснение: Spearman IC — только при ≥3 строках с валидным return на модель; "
            "расширьте datasets/points и пересоберите eval.",
            file=out,
        )
