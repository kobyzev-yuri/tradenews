"""
Локальный Ollama: /api/chat + JSON items → агрегат bias/confidence (как nyse L5).

Запуск модели: ``ollama run llama3.2:3b`` не обязателен — достаточно ``ollama serve`` в фоне;
``run`` — интерактивная сессия. Обычно sudo не нужен.

Переменные окружения (опционально):
  OLLAMA_HOST   — базовый URL (default http://127.0.0.1:11434)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from tradenews.ollama_client import ollama_chat, parse_news_signal_response
from tradenews.predictors.base import NewsPrediction, NewsPredictor
from tradenews.prompt_news_signal import build_ollama_messages
from tradenews.signal_aggregate import aggregate_llm_items


class OllamaNewsPredictor(NewsPredictor):
    """Предиктор: статьи (dict) → Ollama JSON → bias/confidence."""

    def __init__(
        self,
        ollama_model: str,
        *,
        model_id: str | None = None,
        base_url: str | None = None,
        timeout_sec: float = 180.0,
    ) -> None:
        self._ollama_model = ollama_model
        self._model_id = model_id or f"ollama:{ollama_model}"
        self._base_url = (base_url or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self._timeout_sec = timeout_sec

    @property
    def model_id(self) -> str:
        return self._model_id

    def predict(
        self,
        ticker: str,
        decision_ts_utc: datetime,
        *,
        articles_snapshot: Optional[list[dict[str, Any]]] = None,
    ) -> NewsPrediction:
        arts = articles_snapshot or []
        if not arts:
            return NewsPrediction(bias=0.0, confidence=0.0, raw={"reason": "no_articles"})

        messages = build_ollama_messages(ticker, arts, now=decision_ts_utc)
        raw_text = ollama_chat(
            self._ollama_model,
            messages,
            base_url=self._base_url,
            timeout_sec=self._timeout_sec,
            json_mode=True,
        )
        items = parse_news_signal_response(raw_text)
        if len(items) != len(arts):
            # мягкое продолжение: агрегируем то, что разобралось
            pass

        bias, conf = aggregate_llm_items(items)
        return NewsPrediction(
            bias=bias,
            confidence=conf,
            raw={"ollama_model": self._ollama_model, "items": items, "text_len": len(raw_text)},
        )


class OllamaNewsPredictorStub(NewsPredictor):
    """Без сети: всегда нейтрально (юнит-тесты, CI)."""

    def __init__(self, model_id: str = "ollama:stub") -> None:
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    def predict(
        self,
        ticker: str,
        decision_ts_utc: datetime,
        *,
        articles_snapshot: Optional[list[dict[str, Any]]] = None,
    ) -> NewsPrediction:
        return NewsPrediction(bias=0.0, confidence=0.0, raw={"stub": True})
