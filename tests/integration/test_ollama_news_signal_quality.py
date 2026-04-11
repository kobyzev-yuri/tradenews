"""
Качество structured news signal через Ollama (аналог идеи nyse ``test_sentiment_real`` LLM-части,
но без gate/OpenAI — только L5-промпт tradenews + агрегатор bias).

Статьи по умолчанию: ``fixtures/articles/minimal_example.json`` (реальный формат nyse/tradenews).
Переопределить файл:
  TRADENEWS_OLLAMA_ARTICLES_JSON=/path/to/MU_....json

Модели (через запятую или пробел):
  TRADENEWS_OLLAMA_MODELS=llama3.2:3b,qwen2.5:7b

Запуск:
  cd tradenews && PYTHONPATH=. pytest tests/integration/test_ollama_news_signal_quality.py -v -m integration -s

Без Ollama тесты пропускаются (skip).
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

_TRADENEWS_ROOT = Path(__file__).resolve().parent.parent.parent


def _ollama_unreachable_reason(base_url: str) -> str | None:
    url = base_url.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as r:
            if r.status != 200:
                return f"HTTP {r.status}"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def _ollama_models() -> list[str]:
    raw = os.environ.get("TRADENEWS_OLLAMA_MODELS", "llama3.2:3b,qwen2.5:7b")
    parts = []
    for chunk in raw.replace(";", ",").split(","):
        for p in chunk.split():
            p = p.strip()
            if p:
                parts.append(p)
    return parts or ["llama3.2:3b"]


def _articles_path() -> Path:
    env = (os.environ.get("TRADENEWS_OLLAMA_ARTICLES_JSON") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _TRADENEWS_ROOT / "fixtures" / "articles" / "minimal_example.json"


def _load_articles(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"Expected non-empty JSON array in {path}")
    return list(data)


def _decision_ts(articles: list[dict[str, Any]]) -> datetime:
    for a in articles:
        ts = a.get("timestamp")
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _ticker_from_articles(articles: list[dict[str, Any]]) -> str:
    for a in articles:
        t = a.get("ticker")
        if isinstance(t, str) and t.strip():
            return t.strip().upper()
    return "MU"


_ALLOWED_IMPACT = frozenset({"low", "moderate", "high"})
_ALLOWED_REL = frozenset({"mention", "related", "primary"})
_ALLOWED_SURPRISE = frozenset({"none", "minor", "significant", "major"})
_ALLOWED_HORIZON = frozenset({"intraday", "1-3d", "3-7d", "long"})


def _validate_llm_items(items: list[dict[str, Any]], *, n_articles: int) -> None:
    assert items, "LLM вернул пустой items — JSON не разобран или нарушен контракт"
    issues: list[str] = []
    if len(items) != n_articles:
        issues.append(f"len(items)={len(items)} != n_articles={n_articles} (желательно совпадение)")

    for i, it in enumerate(items):
        if not isinstance(it, dict):
            issues.append(f"items[{i}] не объект")
            continue
        try:
            s = float(it["sentiment"])
            if not (-1.0 <= s <= 1.0):
                issues.append(f"items[{i}].sentiment={s} вне [-1,1]")
        except (KeyError, TypeError, ValueError):
            issues.append(f"items[{i}]: невалидный sentiment")

        for key, allowed in (
            ("impact_strength", _ALLOWED_IMPACT),
            ("relevance", _ALLOWED_REL),
            ("surprise", _ALLOWED_SURPRISE),
            ("time_horizon", _ALLOWED_HORIZON),
        ):
            v = str(it.get(key, "")).lower()
            if v not in allowed:
                issues.append(f"items[{i}].{key}={it.get(key)!r} не из {sorted(allowed)}")

        try:
            c = float(it["confidence"])
            if not (0.0 <= c <= 1.0):
                issues.append(f"items[{i}].confidence={c} вне [0,1]")
        except (KeyError, TypeError, ValueError):
            issues.append(f"items[{i}]: невалидный confidence")

    assert not issues, "Проблемы разбора items:\n  " + "\n  ".join(issues)


@pytest.fixture(scope="module")
def ollama_base_url() -> str:
    return (os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")


@pytest.fixture(scope="module")
def require_ollama(ollama_base_url: str):
    reason = _ollama_unreachable_reason(ollama_base_url)
    if reason is not None:
        pytest.skip(f"Ollama недоступен ({ollama_base_url}): {reason}")
    return ollama_base_url


@pytest.fixture(scope="module")
def articles_path() -> Path:
    p = _articles_path()
    if not p.is_file():
        pytest.skip(f"Нет файла статей: {p}")
    return p


@pytest.fixture(scope="module")
def articles_snapshot(articles_path: Path) -> list[dict[str, Any]]:
    return _load_articles(articles_path)


@pytest.mark.integration
@pytest.mark.parametrize("ollama_model", _ollama_models())
def test_ollama_structured_signal_quality(
    require_ollama: str,
    articles_path: Path,
    articles_snapshot: list[dict[str, Any]],
    ollama_model: str,
) -> None:
    """Полный вызов OllamaNewsPredictor: JSON items + bias/confidence в допустимых границах."""
    from tradenews.predictors.ollama import OllamaNewsPredictor

    ticker = _ticker_from_articles(articles_snapshot)
    ts = _decision_ts(articles_snapshot)

    pred = OllamaNewsPredictor(ollama_model, base_url=require_ollama, timeout_sec=240.0)
    try:
        out = pred.predict(ticker, ts, articles_snapshot=articles_snapshot)
    except Exception as exc:
        name = type(exc).__name__
        if any(x in name for x in ("RuntimeError", "Timeout", "URLError", "HTTP")):
            pytest.skip(f"Ollama/сеть: {name}: {exc}")
        raise

    items = out.raw.get("items") if isinstance(out.raw, dict) else None
    assert isinstance(items, list)

    print(
        f"\n[{ollama_model}] articles_file={articles_path.name} n={len(articles_snapshot)} "
        f"bias={out.bias:.4f} confidence={out.confidence:.4f} items={len(items)}"
    )

    assert -1.0 <= out.bias <= 1.0
    assert 0.0 <= (out.confidence or 0.0) <= 1.0

    _validate_llm_items(items, n_articles=len(articles_snapshot))
