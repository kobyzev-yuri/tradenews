"""
Облачный LLM через OpenAI-совместимый ``/v1/chat/completions``.

Переменные окружения (совместимо с корневым ``config.env`` проекта lse):
  OPENAI_API_KEY / OPENAI_GPT_KEY — ключ (достаточно одного)
  OPENAI_BASE_URL — прокси или ``https://api.openai.com/v1``
  OPENAI_MODEL — имя модели, если не заданы аргумент конструктора и ``TRADENEWS_OPENAI_MODEL``
  TRADENEWS_OPENAI_MODEL — перекрывает ``OPENAI_MODEL`` только для tradenews
  OPENAI_TIMEOUT — таймаут запроса, секунды (опционально)
  TRADENEWS_OPENAI_MAX_TOKENS / TRADENEWS_OPENAI_MAX_TOKENS_PARAM — лимит токенов ответа;
    для gpt-5.* и др. клиент шлёт max_completion_tokens (см. openai_chat_client).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from tradenews.ollama_client import parse_news_signal_response
from tradenews.openai_chat_client import openai_chat_completions
from tradenews.predictors.base import NewsPrediction, NewsPredictor
from tradenews.prompt_news_signal import build_ollama_messages
from tradenews.signal_aggregate import aggregate_llm_items


class OpenAINewsPredictor(NewsPredictor):
    """Те же сообщения и агрегатор, что у Ollama; ответ — JSON ``items``."""

    def __init__(
        self,
        openai_model: str | None = None,
        *,
        model_id: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_sec: float = 180.0,
    ) -> None:
        env_model = (os.environ.get("TRADENEWS_OPENAI_MODEL") or "").strip() or (
            os.environ.get("OPENAI_MODEL") or ""
        ).strip()
        self._openai_model = (openai_model or env_model or "gpt-5.4-mini").strip()
        self._model_id = model_id or f"openai:{self._openai_model}"
        key = (
            (api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_GPT_KEY") or "").strip()
        )
        if not key:
            raise ValueError("OPENAI_API_KEY or OPENAI_GPT_KEY is required for OpenAINewsPredictor")
        self._api_key = key
        self._base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip(
            "/"
        )
        to = (os.environ.get("OPENAI_TIMEOUT") or "").strip()
        if to:
            try:
                self._timeout_sec = float(to)
            except ValueError:
                self._timeout_sec = timeout_sec
        else:
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
        raw_text = openai_chat_completions(
            self._openai_model,
            messages,
            api_key=self._api_key,
            base_url=self._base_url,
            timeout_sec=self._timeout_sec,
        )
        items = parse_news_signal_response(raw_text)
        bias, conf = aggregate_llm_items(items)
        return NewsPrediction(
            bias=bias,
            confidence=conf,
            raw={
                "openai_model": self._openai_model,
                "items": items,
                "text_len": len(raw_text),
            },
        )
