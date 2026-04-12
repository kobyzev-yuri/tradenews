"""
Метрики качества news.predict относительно news.val (forward log-returns).

Используются лог-доходности в духе правил проекта lse/nyse.
"""

from __future__ import annotations

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


def confidence_buckets_by_model(
    df: pd.DataFrame,
    *,
    return_col: str,
    confidence_col: str = "confidence_predict",
    n_buckets: int = 4,
    model_col: str = "model_id",
) -> pd.DataFrame:
    """Те же квантили confidence, что ``confidence_bucket_table``, но **отдельно по каждой** ``model_id``."""
    need = {model_col, confidence_col, return_col}
    if not need.issubset(df.columns):
        return pd.DataFrame()
    pieces: list[pd.DataFrame] = []
    for mid, g in df.groupby(model_col, sort=True):
        b = confidence_bucket_table(
            g, confidence_col=confidence_col, return_col=return_col, n_buckets=n_buckets
        )
        if b.empty:
            continue
        bb = b.reset_index()
        bb.insert(0, model_col, str(mid))
        pieces.append(bb)
    if not pieces:
        return pd.DataFrame()
    out = pd.concat(pieces, ignore_index=True)
    return out[[model_col, "bucket", "mean_forward_log_return", "n"]]


def _spearman_corr_numpy(p: np.ndarray, r: np.ndarray) -> float:
    if p.size < 3:
        return float("nan")
    return float(pd.Series(p).corr(pd.Series(r), method="spearman"))


def spearman_bootstrap_ci(
    predict: pd.Series,
    realized: pd.Series,
    *,
    n_bootstrap: int,
    random_seed: int,
) -> tuple[float, float, float]:
    """
    Точечный Spearman + перцентили 2.5 / 97.5 по бутстрепу строк (i.i.d. с возвращением).
    Если слишком мало валидных бутстреп-реплик, границы CI — NaN.
    """
    frame = pd.DataFrame({"p": predict, "r": realized}).dropna()
    if len(frame) < 3:
        return float("nan"), float("nan"), float("nan")
    p = frame["p"].to_numpy(dtype=float)
    r = frame["r"].to_numpy(dtype=float)
    n = len(p)
    point = _spearman_corr_numpy(p, r)
    rng = np.random.default_rng(random_seed)
    vals: list[float] = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        s = _spearman_corr_numpy(p[idx], r[idx])
        if not np.isnan(s):
            vals.append(s)
    min_valid = max(50, n_bootstrap // 10)
    if len(vals) < min_valid:
        return point, float("nan"), float("nan")
    arr = np.asarray(vals, dtype=float)
    lo, hi = np.percentile(arr, [2.5, 97.5])
    return point, float(lo), float(hi)


def spearman_perm_p_two_sided(
    predict: pd.Series,
    realized: pd.Series,
    *,
    n_perm: int,
    random_seed: int,
) -> float:
    """Двусторонний p-value: доля |ρ_perm| ≥ |ρ_obs| при перестановке предиктора."""
    frame = pd.DataFrame({"p": predict, "r": realized}).dropna()
    if len(frame) < 3:
        return float("nan")
    p0 = frame["p"].to_numpy(dtype=float)
    r0 = frame["r"].to_numpy(dtype=float)
    obs = _spearman_corr_numpy(p0, r0)
    if np.isnan(obs):
        return float("nan")
    rng = np.random.default_rng(random_seed)
    count = 0
    for _ in range(n_perm):
        p_shuf = rng.permutation(p0)
        s = _spearman_corr_numpy(p_shuf, r0)
        if np.isnan(s):
            continue
        if abs(s) >= abs(obs):
            count += 1
    return float((1 + count) / (n_perm + 1))


def enrich_summary_with_spearman_uncertainty(
    summary: pd.DataFrame,
    df: pd.DataFrame,
    *,
    return_col: str,
    n_bootstrap: int,
    n_perm: int,
    random_seed: int,
) -> pd.DataFrame:
    if n_bootstrap <= 0 and n_perm <= 0:
        return summary
    extras: list[dict[str, object]] = []
    for i, (mid, g) in enumerate(df.groupby("model_id", sort=True)):
        seed = random_seed + i * 10_007
        row: dict[str, object] = {"model_id": mid}
        if n_bootstrap > 0:
            _, lo, hi = spearman_bootstrap_ci(
                g["bias_predict"], g[return_col], n_bootstrap=n_bootstrap, random_seed=seed
            )
            row["spearman_bootstrap_ci_low"] = lo
            row["spearman_bootstrap_ci_high"] = hi
        if n_perm > 0:
            row["spearman_perm_p_two_sided"] = spearman_perm_p_two_sided(
                g["bias_predict"], g[return_col], n_perm=n_perm, random_seed=seed + 1
            )
        extras.append(row)
    u = pd.DataFrame(extras)
    return summary.merge(u, on="model_id", how="left")


def pairwise_bias_spearman_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    На пересечении (ticker, decision_ts_utc), где есть bias у **всех** моделей:
    попарный Spearman между ``bias_predict`` разных ``model_id``.
    """
    need = {"ticker", "decision_ts_utc", "model_id", "bias_predict"}
    if not need.issubset(df.columns):
        return pd.DataFrame()
    sub = df[list(need)].dropna()
    if sub.empty:
        return pd.DataFrame()
    try:
        wide = sub.pivot_table(
            index=["ticker", "decision_ts_utc"],
            columns="model_id",
            values="bias_predict",
            aggfunc="first",
        )
    except ValueError:
        return pd.DataFrame()
    wide = wide.dropna(how="any")
    if len(wide) < 3:
        return pd.DataFrame()
    models = [str(c) for c in wide.columns]
    mat = wide.to_numpy(dtype=float)
    rows: list[dict[str, object]] = []
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            rho = _spearman_corr_numpy(mat[:, i], mat[:, j])
            rows.append(
                {
                    "model_a": models[i],
                    "model_b": models[j],
                    "n_joint_rows": int(len(wide)),
                    "spearman_bias": rho,
                }
            )
    return pd.DataFrame(rows)


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
    for mid, g in df.groupby("model_id", sort=True):
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
