import pandas as pd

from tradenews.metrics import directional_hit_rate, spearman_ic, summarize_by_model


def test_spearman_ic_perfect_rank():
    p = pd.Series([1.0, 2.0, 3.0, 4.0])
    r = pd.Series([0.1, 0.2, 0.3, 0.4])
    ic = spearman_ic(p, r)
    assert ic > 0.99


def test_hit_rate_sign():
    p = pd.Series([1.0, -1.0, 0.1])
    r = pd.Series([0.5, -0.2, 0.05])
    assert directional_hit_rate(p, r) == 1.0


def test_summarize_by_model():
    df = pd.DataFrame(
        {
            "model_id": ["a", "a", "b", "b"],
            "bias_predict": [0.5, -0.2, 0.1, -0.3],
            "forward_log_return_1d": [0.4, -0.1, -0.05, 0.2],
        }
    )
    s = summarize_by_model(df, return_col="forward_log_return_1d", min_abs_predict=0.05)
    assert set(s["model_id"].tolist()) == {"a", "b"}
    assert (s["n_with_return"] == 2).all()
    assert (s["n_rows"] == 2).all()
