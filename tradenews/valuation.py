"""
Расчёт forward log-returns по ценам закрытия (yfinance).

Без lookahead: опорная цена — первое закрытие строго после ``decision_ts_utc``;
``forward_log_return_hd`` = ln(P[t+h]/P[t]), h шагов по торговым закрытиям вперёд.

yfinance для US-акций часто отдаёт дневной индекс **без timezone** (полуночь в дате торгов).
Сравнение с ``decision_ts_utc`` делаем после приведения индекса к UTC через ``exchange_tz``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

# Псевдо-тикеры LSE knowledge_base (макро-ленты без котировок yfinance)
_TICKERS_SKIP_YFINANCE = frozenset({"US_MACRO", "MACRO", "CASH"})

_logger = logging.getLogger(__name__)


def _null_forward_returns(horizons: tuple[int, ...]) -> dict[str, Optional[float]]:
    return {f"forward_log_return_{h}d": None for h in horizons}


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _index_to_utc(idx: pd.DatetimeIndex, exchange_tz: str) -> pd.DatetimeIndex:
    if idx.tz is None:
        return idx.tz_localize(exchange_tz, ambiguous="infer", nonexistent="shift_forward").tz_convert(
            timezone.utc
        )
    return idx.tz_convert(timezone.utc)


def forward_log_returns_from_close(
    ticker: str,
    decision_ts_utc: datetime,
    *,
    horizons_trading_days: tuple[int, ...] = (1, 3, 5),
    price_buffer_calendar_days: int = 60,
    exchange_tz: str = "America/New_York",
) -> dict[str, Optional[float]]:
    """
    Лог-доходности относительно первого adj close после ``decision_ts_utc``.

    ``forward_log_return_1d`` = ln(P_{t+1}/P_t): первое закрытие после решения → следующее.
    """
    sym = (ticker or "").strip().upper()
    if sym in _TICKERS_SKIP_YFINANCE or not sym:
        return _null_forward_returns(horizons_trading_days)

    t0 = _ensure_utc(decision_ts_utc)
    start = (t0 - timedelta(days=14)).date()
    now_d = datetime.now(timezone.utc).date()
    # Конец окна: и от decision, и не раньше «сегодня+запас», иначе для свежих дат не хватает баров
    end_d = max(
        (t0 + timedelta(days=price_buffer_calendar_days)).date(),
        now_d + timedelta(days=14),
    )

    try:
        hist = yf.Ticker(sym).history(
            start=start,
            end=end_d + timedelta(days=1),
            auto_adjust=True,
            actions=False,
        )
    except Exception as exc:
        _logger.debug("yfinance history failed for %s: %s", sym, exc)
        return _null_forward_returns(horizons_trading_days)
    if hist is None or hist.empty:
        return {f"forward_log_return_{h}d": None for h in horizons_trading_days}

    close = hist["Close"].sort_index()
    idx = close.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.to_datetime(idx, utc=True)
        idx_cmp = idx
    else:
        idx_cmp = _index_to_utc(idx, exchange_tz)

    t_cut = pd.Timestamp(t0)
    if t_cut.tzinfo is None:
        t_cut = t_cut.tz_localize(timezone.utc)
    else:
        t_cut = t_cut.tz_convert(timezone.utc)

    mask = idx_cmp > t_cut
    m = np.asarray(mask, dtype=bool)
    pos = np.flatnonzero(m)
    if len(pos) == 0:
        return {f"forward_log_return_{h}d": None for h in horizons_trading_days}

    prices = close.iloc[pos].to_numpy(dtype=float)
    p0 = float(prices[0])
    out: dict[str, Optional[float]] = {}
    for h in horizons_trading_days:
        if h >= len(prices):
            out[f"forward_log_return_{h}d"] = None
            continue
        p_h = float(prices[h])
        if p0 <= 0 or p_h <= 0 or np.isnan(p0) or np.isnan(p_h):
            out[f"forward_log_return_{h}d"] = None
        else:
            out[f"forward_log_return_{h}d"] = float(np.log(p_h / p0))
    return out
