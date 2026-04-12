"""Сводка метрик по таблице строк (pandas) или JSONL."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from tradenews.io import read_evaluation_rows
from tradenews.metrics import (
    confidence_buckets_by_model,
    enrich_summary_with_spearman_uncertainty,
    summarize_by_model,
)


def evaluation_jsonl_to_dataframe(path: Path | str) -> pd.DataFrame:
    rows = read_evaluation_rows(path)
    return pd.DataFrame([r.to_json_dict() for r in rows])


def compare_models_report(
    df: pd.DataFrame,
    *,
    return_col: str = "forward_log_return_1d",
    min_abs_predict: float = 0.05,
    spearman_bootstrap_n: int = 0,
    spearman_perm_n: int = 0,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Возвращает (summary_by_model, confidence_buckets или пустой).

    Бакеты считаются **отдельно по каждой** ``model_id`` (квантили ``confidence_predict``).
    При ``spearman_bootstrap_n`` / ``spearman_perm_n`` > 0 в summary добавляются
    доверительный интервал и двусторонний p-value для Spearman IC.
    """
    summary = summarize_by_model(df, return_col=return_col, min_abs_predict=min_abs_predict)
    summary = enrich_summary_with_spearman_uncertainty(
        summary,
        df,
        return_col=return_col,
        n_bootstrap=spearman_bootstrap_n,
        n_perm=spearman_perm_n,
        random_seed=random_seed,
    )
    buckets = confidence_buckets_by_model(df, return_col=return_col)
    if buckets is not None and len(buckets) == 0:
        buckets = None
    return summary, buckets


def print_compare_report(path: Path | str, *, return_col: str = "forward_log_return_1d") -> None:
    df = evaluation_jsonl_to_dataframe(path)
    summary, buckets = compare_models_report(df, return_col=return_col)
    print(summary.to_string(index=False))
    if buckets is not None and not buckets.empty:
        print("\n--- confidence buckets (per model) ---")
        for mid, gb in buckets.groupby("model_id", sort=True):
            print(f"\n{mid}")
            print(gb.drop(columns=["model_id"]).to_string(index=False))

    max_valid = int(summary["n_with_return"].max()) if len(summary) and "n_with_return" in summary.columns else 0
    if max_valid < 3:
        print(
            "\n-- Пояснение: Spearman IC считается только при ≥3 строках с валидным "
            f"{return_col} на модель (сейчас максимум {max_valid}). "
            "Добавьте точки в datasets/points/*.jsonl и пересоберите eval.",
        )
    if max_valid >= 1:
        print(
            "-- hit_rate_signed=0.0 на одной строке означает: знак bias_predict не совпал со знаком "
            f"{return_col} (или оба нули). NaN в колонке hit_rate_|bias|>=…: ни одна строка не прошла порог по |bias|.",
        )
