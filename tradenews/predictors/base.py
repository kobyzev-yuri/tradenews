"""Абстракция предиктора: контекст → bias (+ confidence)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class NewsPrediction:
    """Результат одного предиктора для одной точки датасета."""

    bias: float
    confidence: Optional[float] = None
    raw: Optional[dict[str, Any]] = None


@runtime_checkable
class NewsPredictor(Protocol):
    """Плагин: реализации — Ollama, nyse pipeline, baseline cheap_sentiment."""

    @property
    def model_id(self) -> str: ...

    def predict(
        self,
        ticker: str,
        decision_ts_utc: datetime,
        *,
        articles_snapshot: Optional[list[dict[str, Any]]] = None,
    ) -> NewsPrediction:
        ...
