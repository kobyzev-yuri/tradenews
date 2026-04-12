"""
DeepSeek через OpenAI-совместимый ``/v1/chat/completions`` (прямой API или **ProxyAPI**).

**ProxyAPI** (один ключ ``PROXYAPI_KEY``): универсальный endpoint
``https://openai.api.proxyapi.ru/v1``; модель для reasoner по умолчанию маппится на
``openrouter/deepseek/deepseek-r1-0528`` (см. ``tradenews.proxyapi`` и
``TRADENEWS_PROXYAPI_DEEPSEEK_REASONER_MODEL`` / ``_CHAT_MODEL``). Выделенный DeepSeek API у ProxyAPI
в документации помечен устаревшим в пользу OpenRouter-ветки.

Без ProxyAPI (прямой DeepSeek):
  DEEPSEEK_API_KEY — обязательно
  DEEPSEEK_BASE_URL — по умолчанию ``https://api.deepseek.com/v1``
  DEEPSEEK_TIMEOUT — таймаут секунд (для reasoner часто 300–600)
  TRADENEWS_DEEPSEEK_JSON_OBJECT — ``0`` отключает ``response_format: json_object``, если API ругается

С ProxyAPI дополнительно: ``PROXYAPI_TIMEOUT`` (иначе как у прямого режима).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from tradenews import proxyapi as proxyapi
from tradenews.ollama_client import parse_news_signal_response
from tradenews.openai_chat_client import openai_chat_completions
from tradenews.predictors.base import NewsPrediction, NewsPredictor
from tradenews.prompt_news_signal import build_ollama_messages
from tradenews.signal_aggregate import aggregate_llm_items


def _deepseek_want_json_object() -> bool:
    override = (os.environ.get("TRADENEWS_DEEPSEEK_JSON_OBJECT") or "").strip().lower()
    if override in ("0", "false", "no"):
        return False
    if override in ("1", "true", "yes"):
        return True
    return (os.environ.get("TRADENEWS_OPENAI_JSON_OBJECT") or "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


class DeepSeekNewsPredictor(NewsPredictor):
    """Те же сообщения и парсер, что у OpenAI/Ollama; endpoint DeepSeek."""

    def __init__(
        self,
        deepseek_model: str,
        *,
        model_id: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        self._logical_model = deepseek_model.strip()
        if not self._logical_model:
            raise ValueError("DeepSeek model id is empty")
        self._model_id = model_id or f"deepseek:{self._logical_model}"
        if proxyapi.use_proxyapi_routing():
            pk = (api_key or proxyapi.proxyapi_key() or "").strip()
            if not pk:
                raise ValueError(
                    "ProxyAPI: задайте PROXYAPI_KEY (tradenews/config.env) или см. цепочку ключей в tradenews.proxyapi"
                )
            self._api_key = pk
            self._base_url = (base_url or proxyapi.chat_completions_base_url(multivendor=True)).rstrip("/")
            self._chat_model = proxyapi.api_model_for_deepseek(self._logical_model)
        else:
            key = (api_key or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
            if not key:
                raise ValueError("DEEPSEEK_API_KEY is required for DeepSeekNewsPredictor")
            self._api_key = key
            self._base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip(
                "/"
            )
            self._chat_model = self._logical_model
        if timeout_sec is not None:
            self._timeout_sec = float(timeout_sec)
        else:
            if proxyapi.use_proxyapi_routing():
                to = (
                    os.environ.get("PROXYAPI_TIMEOUT")
                    or os.environ.get("DEEPSEEK_TIMEOUT")
                    or os.environ.get("OPENAI_TIMEOUT")
                    or ""
                ).strip()
            else:
                to = (os.environ.get("DEEPSEEK_TIMEOUT") or "").strip()
            if to:
                try:
                    self._timeout_sec = float(to)
                except ValueError:
                    self._timeout_sec = 600.0 if "reasoner" in self._logical_model.lower() else 180.0
            else:
                self._timeout_sec = 600.0 if "reasoner" in self._logical_model.lower() else 180.0

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
            self._chat_model,
            messages,
            api_key=self._api_key,
            base_url=self._base_url,
            timeout_sec=self._timeout_sec,
            json_response=_deepseek_want_json_object(),
        )
        items = parse_news_signal_response(raw_text)
        bias, conf = aggregate_llm_items(items)
        raw_out: dict[str, Any] = {
            "deepseek_model": self._logical_model,
            "items": items,
            "text_len": len(raw_text),
        }
        if self._chat_model != self._logical_model:
            raw_out["chat_completions_model"] = self._chat_model
        return NewsPrediction(
            bias=bias,
            confidence=conf,
            raw=raw_out,
        )
