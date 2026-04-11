"""benchmark_report: сводка по нескольким горизонтам."""

from __future__ import annotations

import pandas as pd

from tradenews.benchmark_report import build_benchmark_report


def test_build_benchmark_report_multi_model():
    df = pd.DataFrame(
        {
            "model_id": ["ollama:a", "ollama:a", "ollama:a", "ollama:b", "ollama:b", "ollama:b"],
            "bias_predict": [0.2, -0.1, 0.15, 0.1, -0.2, 0.05],
            "forward_log_return_1d": [0.02, -0.01, 0.01, 0.03, -0.02, 0.0],
            "forward_log_return_3d": [0.03, 0.0, -0.01, 0.02, 0.01, -0.01],
            "forward_log_return_5d": [0.04, 0.01, 0.0, 0.0, 0.02, 0.01],
            "confidence_predict": [0.8, 0.7, 0.9, 0.6, 0.85, 0.75],
        }
    )
    rep = build_benchmark_report(
        df,
        horizons=("forward_log_return_1d", "forward_log_return_3d"),
        eval_path="/tmp/x.jsonl",
    )
    assert rep["meta"]["n_rows"] == 6
    assert set(rep["meta"]["model_ids"]) == {"ollama:a", "ollama:b"}
    h1 = rep["horizons"]["forward_log_return_1d"]
    assert len(h1["summary"]) == 2
    assert len(h1["ranking_by_spearman_ic"]) == 2
    assert h1["ranking_by_spearman_ic"][0]["model_id"] in ("ollama:a", "ollama:b")
