from datetime import datetime, timezone

from tradenews.valuation import forward_log_returns_from_close


def test_skip_us_macro_no_yfinance_call():
    out = forward_log_returns_from_close(
        "US_MACRO",
        datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
    )
    assert out["forward_log_return_1d"] is None
    assert out["forward_log_return_3d"] is None


def test_skip_macro_and_cash():
    for t in ("MACRO", "CASH", "macro"):
        out = forward_log_returns_from_close(
            t,
            datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
        )
        assert all(v is None for v in out.values())
