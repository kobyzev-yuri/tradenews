"""Минимальный клиент Ollama /api/chat (stdlib, без зависимостей)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


def _parse_keep_alive(raw: str) -> str | int:
    """
    Значение для поля JSON ``keep_alive``: секунды (int) или строка вроде ``30m``, ``-1`` (вечно).
    См. https://github.com/ollama/ollama/blob/main/docs/api.md
    """
    s = raw.strip()
    if not s:
        raise ValueError("empty keep_alive")
    if s.lstrip("-").isdigit():
        return int(s)
    return s


def strip_json_fence(raw: str) -> str:
    s = raw.strip()
    if not s.startswith("```"):
        return s
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def ollama_chat(
    model: str,
    messages: list[dict[str, str]],
    *,
    base_url: str = "http://127.0.0.1:11434",
    timeout_sec: float = 180.0,
    json_mode: bool = True,
    keep_alive: str | int | None = None,
) -> str:
    """
    POST /api/chat, возвращает текст ответа ассистента (сырой).

    ``keep_alive``: сколько держать модель в VRAM после ответа (например ``\"30m\"``, ``-1``).
    Если ``None``, берётся ``OLLAMA_KEEP_ALIVE`` из окружения; если и оно пусто — поле не шлём (дефолт сервера Ollama, обычно несколько минут).
    """
    url = base_url.rstrip("/") + "/api/chat"
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if json_mode:
        body["format"] = "json"

    ka_env = (os.environ.get("OLLAMA_KEEP_ALIVE") or "").strip()
    ka = keep_alive
    if ka is None and ka_env:
        try:
            body["keep_alive"] = _parse_keep_alive(ka_env)
        except ValueError:
            pass
    elif ka is not None:
        body["keep_alive"] = ka if isinstance(ka, int) else _parse_keep_alive(str(ka))

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama connection failed: {e}") from e

    msg = payload.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"Unexpected Ollama response: {payload!r}")
    return content


def parse_news_signal_response(raw: str) -> list[dict[str, Any]]:
    """Разбор JSON {\"items\": [...]} после strip_json_fence."""
    text = strip_json_fence(raw)
    data = json.loads(text)
    if not isinstance(data, dict) or "items" not in data:
        raise ValueError("Response must be a JSON object with 'items' array")
    items = data["items"]
    if not isinstance(items, list) or not items:
        raise ValueError("'items' must be a non-empty list")
    out: list[dict[str, Any]] = []
    for it in items:
        if isinstance(it, dict):
            out.append(it)
    if len(out) != len(items):
        raise ValueError("Each item must be an object")
    out.sort(key=lambda x: int(x.get("article_index", 0)))
    return out
