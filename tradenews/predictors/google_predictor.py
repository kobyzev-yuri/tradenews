"""
Google Gemini: нативный Generativelanguage API **или** тот же OpenAI-совместимый шлюз **ProxyAPI**.

**ProxyAPI**: при ``PROXYAPI_KEY`` + ``OPENAI_BASE_URL=…proxyapi.ru…`` (и включённом маршруте, см. ``proxyapi.py``) запросы идут
через шлюз ProxyAPI с моделью
``gemini/<имя>`` (см. [модели Google в ProxyAPI](https://proxyapi.ru/docs/google-models)), один Bearer-ключ.

Без ProxyAPI:
  GEMINI_API_KEY или GOOGLE_API_KEY — ключ (достаточно одного)
  TRADENEWS_GEMINI_MODEL — модель по умолчанию, если не передана в конструктор (напр. gemini-2.0-flash)
  TRADENEWS_GEMINI_TIMEOUT — таймаут секунд
  TRADENEWS_GEMINI_JSON — ``0`` отключает ``responseMimeType: application/json`` (только нативный API)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional

from tradenews import proxyapi as proxyapi
from tradenews.gemini_client import gemini_generate_text
from tradenews.ollama_client import parse_news_signal_response
from tradenews.openai_chat_client import openai_chat_completions
from tradenews.predictors.base import NewsPrediction, NewsPredictor
from tradenews.prompt_news_signal import (
    OLLAMA_JSON_SUFFIX,
    SCHEMA_HINT,
    SYSTEM_PROMPT,
    USER_PROMPT_CORE,
    articles_dicts_to_payload,
    build_ollama_messages,
)
from tradenews.signal_aggregate import aggregate_llm_items


class GoogleNewsPredictor(NewsPredictor):
    """Gemini: system + user текст как у Ollama; ответ JSON ``items``."""

    def __init__(
        self,
        gemini_model: str | None = None,
        *,
        model_id: str | None = None,
        api_key: str | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        env_m = (os.environ.get("TRADENEWS_GEMINI_MODEL") or "").strip()
        self._logical_model = (gemini_model or env_m or "gemini-2.0-flash").strip()
        if not self._logical_model:
            raise ValueError("Gemini model id is empty")
        self._model_id = model_id or f"google:{self._logical_model}"
        if proxyapi.use_proxyapi_routing():
            pk = (api_key or proxyapi.proxyapi_key() or "").strip()
            if not pk:
                raise ValueError(
                    "ProxyAPI: задайте PROXYAPI_KEY (tradenews/config.env) или см. цепочку ключей в tradenews.proxyapi"
                )
            self._api_key = pk
            self._base_url = proxyapi.chat_completions_base_url(multivendor=True).rstrip("/")
            self._chat_model = proxyapi.api_model_for_gemini(self._logical_model)
            self._use_proxyapi = True
        else:
            key = (
                api_key
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
                or ""
            ).strip()
            if not key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required for GoogleNewsPredictor")
            self._api_key = key
            self._use_proxyapi = False
            self._base_url = ""
            self._chat_model = self._logical_model
        if timeout_sec is not None:
            self._timeout_sec = float(timeout_sec)
        else:
            if self._use_proxyapi:
                to = (
                    os.environ.get("PROXYAPI_TIMEOUT")
                    or os.environ.get("TRADENEWS_GEMINI_TIMEOUT")
                    or os.environ.get("OPENAI_TIMEOUT")
                    or ""
                ).strip()
            else:
                to = (os.environ.get("TRADENEWS_GEMINI_TIMEOUT") or "").strip()
            self._timeout_sec = float(to) if to else 180.0

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

        want_json = (os.environ.get("TRADENEWS_GEMINI_JSON") or "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if self._use_proxyapi:
            messages = build_ollama_messages(ticker, arts, now=decision_ts_utc)
            raw_text = openai_chat_completions(
                self._chat_model,
                messages,
                api_key=self._api_key,
                base_url=self._base_url,
                timeout_sec=self._timeout_sec,
                json_response=want_json,
            )
        else:
            payload = articles_dicts_to_payload(ticker, arts, now=decision_ts_utc)
            core = USER_PROMPT_CORE.format(
                payload=json.dumps(payload, ensure_ascii=False, indent=2),
            )
            user = core + "\n\n" + OLLAMA_JSON_SUFFIX.format(schema_hint=SCHEMA_HINT)
            raw_text = gemini_generate_text(
                self._logical_model,
                system_instruction=SYSTEM_PROMPT,
                user_text=user,
                api_key=self._api_key,
                timeout_sec=self._timeout_sec,
                response_mime_json=want_json,
            )
        items = parse_news_signal_response(raw_text)
        bias, conf = aggregate_llm_items(items)
        raw_out: dict[str, Any] = {
            "gemini_model": self._logical_model,
            "items": items,
            "text_len": len(raw_text),
        }
        if self._use_proxyapi and self._chat_model != self._logical_model:
            raw_out["chat_completions_model"] = self._chat_model
        return NewsPrediction(
            bias=bias,
            confidence=conf,
            raw=raw_out,
        )
