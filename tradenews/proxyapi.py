"""
[ProxyAPI](https://proxyapi.ru/docs/openai-compatible-api): один ключ и OpenAI-совместимые эндпоинты.

В **tradenews/config.env** достаточно ``PROXYAPI_KEY`` + ``OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1``
(и при желании ``TRADENEWS_USE_PROXYAPI=1``). В корневом **lse/config.env** для других сервисов по-прежнему
может быть ``OPENAI_GPT_KEY`` — tradenews подставит его только если ``PROXYAPI_KEY`` пуст.

Два стиля базы:
- **Сегмент OpenAI** ``https://api.proxyapi.ru/openai/v1`` — в теле запроса модель **без** префикса ``openai/`` (как у официального OpenAI).
- **Универсальный** ``https://openai.api.proxyapi.ru/v1`` — модели вида ``openai/…``, ``gemini/…``, ``openrouter/deepseek/…``.

Если задан только сегмент ``…/openai/v1``, запросы **OpenAI** идут туда; Gemini и DeepSeek автоматически
переключаются на универсальный хост (тот же ключ Bearer).

Рекомендуемая связка в **tradenews/config.env**: ``PROXYAPI_KEY=…`` + ``TRADENEWS_USE_PROXYAPI=1``.
Цепочка ключа: ``PROXYAPI_KEY`` → ``TRADENEWS_PROXYAPI_KEY`` → ``OPENAI_GPT_KEY`` → ``OPENAI_API_KEY``.

Отключить ProxyAPI: ``TRADENEWS_USE_PROXYAPI=0`` (или ``false`` / ``no``).
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

DEFAULT_OPENAI_COMPAT_BASE = "https://openai.api.proxyapi.ru/v1"


def proxyapi_key() -> str | None:
    """Ключ ProxyAPI: отдельная переменная или тот же, что для OpenAI в lse (``OPENAI_GPT_KEY`` / ``OPENAI_API_KEY``)."""
    for name in ("PROXYAPI_KEY", "TRADENEWS_PROXYAPI_KEY", "OPENAI_GPT_KEY", "OPENAI_API_KEY"):
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return None


def _openai_base_url_raw() -> str:
    return (os.environ.get("OPENAI_BASE_URL") or "").strip().rstrip("/")


def openai_base_url_is_proxyapi() -> bool:
    return "proxyapi.ru" in _openai_base_url_raw().lower()


def use_proxyapi_routing() -> bool:
    flag = (os.environ.get("TRADENEWS_USE_PROXYAPI") or "").strip().lower()
    if flag in ("0", "false", "no"):
        return False
    if flag in ("1", "true", "yes") and proxyapi_key():
        return True
    if (os.environ.get("PROXYAPI_KEY") or os.environ.get("TRADENEWS_PROXYAPI_KEY") or "").strip():
        return True
    if openai_base_url_is_proxyapi() and proxyapi_key():
        return True
    return False


def _endpoint_kind(base_url: str) -> str:
    """``unified`` | ``openai_segment`` | ``other``."""
    u = urlparse(base_url)
    host = (u.netloc or "").lower()
    path = (u.path or "").rstrip("/")
    if "openai.api.proxyapi.ru" in host:
        return "unified"
    if "proxyapi.ru" in host and path.endswith("/openai/v1"):
        return "openai_segment"
    if "proxyapi.ru" in host:
        return "unified"
    return "other"


def proxy_primary_base_url() -> str:
    o = (os.environ.get("TRADENEWS_OPENAI_COMPAT_BASE_URL") or "").strip().rstrip("/")
    if o:
        return o
    ob = _openai_base_url_raw()
    if openai_base_url_is_proxyapi():
        return ob
    return DEFAULT_OPENAI_COMPAT_BASE.rstrip("/")


def chat_completions_base_url(*, multivendor: bool) -> str:
    """
    ``multivendor=False`` — база для предиктора OpenAI (как в ``OPENAI_BASE_URL`` при ProxyAPI).
    ``multivendor=True`` — для Gemini/DeepSeek; при сегменте ``…/openai/v1`` подмена на универсальный хост.
    """
    primary = proxy_primary_base_url()
    if not multivendor:
        return primary
    if _endpoint_kind(primary) == "openai_segment":
        return DEFAULT_OPENAI_COMPAT_BASE.rstrip("/")
    return primary


def openai_compat_base_url() -> str:
    """Совместимость со старым вызовом: первичная база (как ``proxy_primary_base_url``)."""
    return proxy_primary_base_url()


def api_model_for_openai(logical: str, *, chat_base_url: str | None = None) -> str:
    """Логическое имя из спеки ``openai:…`` → идентификатор для chat/completions."""
    s = logical.strip()
    if not s:
        raise ValueError("empty OpenAI logical model")
    if "/" in s:
        return s
    base = (chat_base_url or proxy_primary_base_url()).rstrip("/")
    if _endpoint_kind(base) == "unified":
        return f"openai/{s}"
    return s


def api_model_for_gemini(logical: str) -> str:
    s = logical.strip()
    if not s:
        raise ValueError("empty Gemini logical model")
    low = s.lower()
    if low.startswith("gemini/"):
        return s
    return f"gemini/{s}"


def api_model_for_deepseek(logical: str) -> str:
    s = logical.strip()
    if not s:
        raise ValueError("empty DeepSeek logical model")
    if "/" in s:
        return s
    low = s.lower()
    if "reasoner" in low or low.endswith("r1") or "r1-" in low or "deepseek-r1" in low:
        return (
            os.environ.get("TRADENEWS_PROXYAPI_DEEPSEEK_REASONER_MODEL") or "openrouter/deepseek/deepseek-r1-0528"
        ).strip()
    return (os.environ.get("TRADENEWS_PROXYAPI_DEEPSEEK_CHAT_MODEL") or "openrouter/deepseek/deepseek-chat-v3.1").strip()
