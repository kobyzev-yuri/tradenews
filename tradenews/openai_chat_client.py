"""Клиент OpenAI-совместимого Chat Completions API (stdlib, без openai-пакета)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from tradenews.ollama_client import strip_json_fence


def _model_tail_for_token_policy(model: str) -> str:
    """Учитывает идентификаторы ProxyAPI вида ``openai/gpt-5…`` / ``gemini/…`` / ``openrouter/…``."""
    m = model.strip().lower()
    if "/" in m:
        m = m.split("/", 1)[1]
    return m


def _completion_tokens_field(model: str) -> str:
    """Chat Completions: новые модели (gpt-5.*, gpt-4.1*, o-series) требуют ``max_completion_tokens``."""
    override = (os.environ.get("TRADENEWS_OPENAI_MAX_TOKENS_PARAM") or "").strip().lower()
    if override in ("max_tokens", "max_completion_tokens"):
        return override
    m = _model_tail_for_token_policy(model)
    if m.startswith("deepseek"):
        return "max_tokens"
    if m.startswith("gpt-5") or m.startswith("gpt-4.1"):
        return "max_completion_tokens"
    if m.startswith(("o1", "o3", "o4")):
        return "max_completion_tokens"
    return "max_tokens"


def openai_chat_completions(
    model: str,
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    timeout_sec: float = 180.0,
    temperature: float = 0.1,
    use_json_object_format: bool = True,
    json_response: bool | None = None,
) -> str:
    """
    POST ``{base_url}/chat/completions``, возвращает текст ассистента.

    ``api_key``: или явный ключ, или из окружения (вызывающий код обычно передаёт
    ``os.environ["OPENAI_API_KEY"]``).

    ``use_json_object_format``: вместе с ``TRADENEWS_OPENAI_JSON_OBJECT`` включает JSON-режим.

    ``json_response``: если не ``None``, задаёт включение ``response_format`` напрямую
    (для сторонних OpenAI-совместимых API, например DeepSeek, без привязки к env OpenAI).

    Лимит ответа: ``TRADENEWS_OPENAI_MAX_TOKENS`` (число). Для gpt-5 / gpt-4.1 / o-series
    в тело кладётся ``max_completion_tokens``; для остальных — ``max_tokens``.
    Принудительно: ``TRADENEWS_OPENAI_MAX_TOKENS_PARAM=max_completion_tokens`` или ``max_tokens``.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_response is not None:
        want_json = bool(json_response)
    else:
        want_json = use_json_object_format and (
            os.environ.get("TRADENEWS_OPENAI_JSON_OBJECT") or "1"
        ).strip().lower() in (
            "1",
            "true",
            "yes",
        )
    if want_json:
        body["response_format"] = {"type": "json_object"}

    max_tok = (os.environ.get("TRADENEWS_OPENAI_MAX_TOKENS") or "").strip()
    n = int(max_tok) if max_tok.isdigit() else 4096
    body[_completion_tokens_field(model)] = n

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        hint = ""
        if e.code == 401 and "proxyapi.ru" in base_url.lower():
            hint = (
                " | Подсказка: для ProxyAPI нужен ключ из https://console.proxyapi.ru/ в PROXYAPI_KEY "
                "(tradenews/config.env). Если PROXYAPI_KEY пуст, берётся OPENAI_GPT_KEY из lse — "
                "он должен быть ключом ProxyAPI, не «чистым» OpenAI."
            )
        raise RuntimeError(f"OpenAI HTTP {e.code}: {err_body[:4000]}{hint}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAI connection failed: {e}") from e

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"OpenAI unexpected payload (no choices): {str(payload)[:2000]}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"OpenAI unexpected message.content: {payload!r}")
    return strip_json_fence(content)
