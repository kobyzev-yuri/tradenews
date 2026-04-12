"""Дефолты для сборки eval / бенчмарка (несколько моделей: Ollama + облако через ProxyAPI)."""

from __future__ import annotations

import os

DEFAULT_OLLAMA_MODELS_FOR_BENCHMARK: tuple[str, ...] = (
    "llama3.2:3b",
    "qwen2.5:7b",
)


def default_openai_model_id() -> str:
    """Один id OpenAI для встроенного дефолтного списка (если не задан ``TRADENEWS_EVAL_MODEL_SPECS``)."""
    return (os.environ.get("TRADENEWS_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL") or "").strip() or "gpt-5.4-mini"


def default_build_model_specs() -> list[str]:
    """
    Спеки для ``run_model_benchmark --build`` без ``--models``.

    Если в окружении задан ``TRADENEWS_EVAL_MODEL_SPECS`` (через запятую или пробел) — используется он,
    иначе фиксированный набор: два Ollama + ``openai:${OPENAI_MODEL}`` + Gemini.
    """
    raw = (os.environ.get("TRADENEWS_EVAL_MODEL_SPECS") or "").strip()
    if raw:
        parts = [p.strip() for p in raw.replace(",", " ").split() if p.strip()]
        if parts:
            return parts
    return [
        *DEFAULT_OLLAMA_MODELS_FOR_BENCHMARK,
        f"openai:{default_openai_model_id()}",
        "google:gemini-2.0-flash",
    ]
