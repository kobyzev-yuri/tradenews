"""
Взвешенная агрегатция сигналов по статьям — та же логика, что nyse ``aggregate_news_signals``,
но от строковых полей ответа LLM (без импорта domain.NewsSignal).
"""

from __future__ import annotations

from typing import Any

# Значения — как в nyse / pystockinvest
_RELEVANCE_W = {"mention": 0.4, "related": 0.7, "primary": 1.0}
_IMPACT_W = {"low": 0.4, "moderate": 0.7, "high": 1.0}
_HORIZON_W = {"intraday": 0.8, "1-3d": 1.0, "3-7d": 0.6, "long": 0.3}


def aggregate_llm_items(items: list[dict[str, Any]]) -> tuple[float, float]:
    """
    Возвращает (bias, confidence) из списка объектов с полями:
    sentiment, impact_strength, relevance, time_horizon, confidence.
    """
    if not items:
        return 0.0, 0.0

    weighted_sum = 0.0
    weight_sum = 0.0
    confidence_sum = 0.0

    for it in items:
        try:
            sent = float(it["sentiment"])
            sent = max(-1.0, min(1.0, sent))
            rel = str(it["relevance"]).lower()
            imp = str(it["impact_strength"]).lower()
            hor = str(it["time_horizon"]).lower()
            conf = float(it["confidence"])
        except (KeyError, TypeError, ValueError):
            continue

        wr = _RELEVANCE_W.get(rel)
        wi = _IMPACT_W.get(imp)
        wh = _HORIZON_W.get(hor)
        if wr is None or wi is None or wh is None:
            continue

        w = wr * wi * wh * max(conf, 0.05)
        weighted_sum += sent * w
        confidence_sum += conf * w
        weight_sum += w

    if weight_sum <= 0.0:
        return 0.0, 0.0

    return weighted_sum / weight_sum, confidence_sum / weight_sum
