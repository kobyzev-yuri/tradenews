"""Клиент Google Gemini (generateContent, v1beta), stdlib — без SDK."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from tradenews.ollama_client import strip_json_fence


def gemini_generate_text(
    model: str,
    *,
    system_instruction: str,
    user_text: str,
    api_key: str,
    timeout_sec: float = 180.0,
    temperature: float = 0.1,
    max_output_tokens: int | None = None,
    response_mime_json: bool = True,
) -> str:
    """
    POST ``v1beta/models/{model}:generateContent``, возвращает текст первой части ответа.

    ``response_mime_json``: ``generationConfig.responseMimeType=application/json`` (Gemini 1.5+ / 2.x).
    """
    m = model.strip()
    if not m:
        raise ValueError("empty Gemini model id")
    enc_model = urllib.parse.quote(m, safe="")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{enc_model}:generateContent"
        f"?key={urllib.parse.quote(api_key, safe='')}"
    )
    mot = max_output_tokens
    if mot is None:
        raw = (os.environ.get("TRADENEWS_GEMINI_MAX_OUTPUT_TOKENS") or "").strip()
        mot = int(raw) if raw.isdigit() else 8192
    gen_cfg: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": int(mot),
    }
    if response_mime_json:
        gen_cfg["responseMimeType"] = "application/json"

    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": gen_cfg,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
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
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {e.code}: {err_body[:4000]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Gemini connection failed: {e}") from e

    cand = (payload.get("candidates") or [])
    if not isinstance(cand, list) or not cand:
        raise RuntimeError(f"Gemini unexpected payload (no candidates): {str(payload)[:2000]}")
    content = cand[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts or not isinstance(parts[0], dict):
        raise RuntimeError(f"Gemini unexpected content.parts: {payload!r}")
    text = parts[0].get("text")
    if not isinstance(text, str):
        raise RuntimeError(f"Gemini unexpected part text: {payload!r}")
    return strip_json_fence(text)
