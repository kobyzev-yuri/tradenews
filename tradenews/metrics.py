"""
Метрики качества news.predict относительно news.val (forward log-returns).

Используются лог-доходности в духе правил проекта lse/nyse.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def spearman_ic(predict: pd.Series, realized: pd.Series) -> float:
    """Spearman correlation; NaN пары отбрасываются."""
    df = pd.DataFrame({"p": predict, "r": realized}).dropna()
    if len(df) < 3:
        return float("nan")
    return float(df["p"].corr(df["r"], method="spearman"))


def directional_hit_rate(
    predict: pd.Series,
    realized: pd.Series,
    *,
    min_abs_predict: float = 0.0,
) -> float:
    """Доля совпадения знака predict и realized; опционально только |predict| >= threshold."""
    df = pd.DataFrame({"p": predict, "r": realized}).dropna()
    if min_abs_predict > 0:
        df = df[df["p"].abs() >= min_abs_predict]
    if len(df) == 0:
        return float("nan")
    same = ((df["p"] > 0) & (df["r"] > 0)) | ((df["p"] < 0) & (df["r"] < 0)) | ((df["p"] == 0) & (df["r"] == 0))
    return float(same.mean())


def confidence_bucket_table(
    df: pd.DataFrame,
    *,
    confidence_col: str = "confidence_predict",
    return_col: str = "forward_log_return_1d",
    n_buckets: int = 4,
) -> pd.DataFrame:
    """Средний forward return и число строк по квантилям confidence."""
    sub = df[[confidence_col, return_col]].dropna()
    if len(sub) < n_buckets * 2:
        return pd.DataFrame()
    try:
        sub = sub.assign(
            bucket=pd.qcut(sub[confidence_col].rank(method="first"), n_buckets, labels=False, duplicates="drop")
        )
    except ValueError:
        return pd.DataFrame()
    return (
        sub.groupby("bucket", observed=True)[return_col]
        .agg(["mean", "count"])
        .rename(columns={"mean": "mean_forward_log_return", "count": "n"})
    )


def summarize_by_model(
    df: pd.DataFrame,
    *,
    return_col: str = "forward_log_return_1d",
    min_abs_predict: float = 0.05,
) -> pd.DataFrame:
    """
    IC, hit rate по каждой ``model_id``.

    Ожидаемые колонки: ``model_id``, ``bias_predict``, ``{return_col}``,
    опционально ``confidence_predict``.
    """
    rows: list[dict] = []
    for mid, g in df.groupby("model_id"):
        pred = g["bias_predict"]
        ret = g[return_col]
        ic = spearman_ic(pred, ret)
        hit = directional_hit_rate(pred, ret, min_abs_predict=min_abs_predict)
        hit_any = directional_hit_rate(pred, ret, min_abs_predict=0.0)
        n_valid = int(g[return_col].notna().sum())
        rows.append(
            {
                "model_id": mid,
                "n_rows": len(g),
                "n_with_return": n_valid,
                "spearman_ic": ic,
                "hit_rate_signed": hit_any,
                f"hit_rate_|bias|>={min_abs_predict}": hit,
            }
        )
    return pd.DataFrame(rows)
