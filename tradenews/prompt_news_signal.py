"""
Промпт уровня L5: **ядро** совпадает с nyse ``pipeline/news/news_signal_prompt.py``
(``SYSTEM_PROMPT`` и ``USER_PROMPT_CORE`` — дословно).

В nyse схема ответа задаётся Pydantic / ``with_structured_output(NewsSignalLLMResponse)``;
для Ollama без того же контракта на стороне API к user-сообщению добавляется
``OLLAMA_JSON_SUFFIX`` с явным JSON-шаблоном (тот же набор полей, что ``NewsSignalLLMItem``).

Канон (править там первым делом): репозиторий nyse, файл
``pipeline/news/news_signal_prompt.py``. Инкремент ``PROMPT_VERSION`` должен совпадать
с nyse при изменении SYSTEM/USER core — сброс LLM-кэша.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

# Дословно из nyse/pipeline/news/news_signal_prompt.py
SYSTEM_PROMPT = """
You are a financial news analyst for stock prediction.
For each article, estimate the expected effect on the target ticker.

Your output should help determine the likely direction, strength, and duration of the target ticker's price move.
Be conservative when relevance is weak.

Each structured signal must be internally consistent and usable for downstream aggregation:
- sentiment (required): float in [-1, 1] = your expectation of direction and strength of price impact on the **target ticker** (negative bearish, positive bullish). This is not merely "tone of the article" if the ticker is only peripheral.
- impact_strength: scale of how large a move you expect **given** that direction (low / moderate / high).
- relevance: how central the target ticker is to the story (mention / related / primary).
- time_horizon: when the effect mainly materializes (intraday / 1-3d / 3-7d / long). Align with your short-term framing where appropriate.
- confidence: float in [0, 1] = certainty in this article-level signal.
- surprise: newsworthiness vs expectations; it is stored but **does not** enter the numeric bias weighting (relevance × impact × horizon × confidence).

Return only the structured output.
""".strip()

# Дословно user-часть nyse (без Ollama-приложения)
USER_PROMPT_CORE = """
Analyze each article independently for its likely effect on the target ticker.
Analyze in context of short-term price move (over next 1-3 days).
Return exactly one signal per article, in the same order as provided.

Input:
{payload}
""".strip()

# Совпадает с nyse ``news_signal_prompt`` (сброс кэша при правке SYSTEM/USER core)
PROMPT_VERSION = "v4"

# Только для Ollama / JSON в тексте: поля как ``NewsSignalLLMItem`` (news_dto.py)
OLLAMA_JSON_SUFFIX = """
When returning JSON (no markdown fences), use exactly this shape. Field values must match the allowed strings below (lowercase).

{schema_hint}
""".strip()

SCHEMA_HINT = """{
  "items": [
    {
      "article_index": 1,
      "sentiment": 0.0,
      "impact_strength": "low" | "moderate" | "high",
      "relevance": "mention" | "related" | "primary",
      "surprise": "none" | "minor" | "significant" | "major",
      "time_horizon": "intraday" | "1-3d" | "3-7d" | "long",
      "confidence": 0.0
    }
  ]
}

Rules:
- One object per input article; article_index must be 1..n in order matching the input articles.
- sentiment: float in [-1, 1] = expected direction/strength of effect on the **target ticker** price (bearish negative, bullish positive). Not "tone of article" alone.
- impact_strength: scale of move **given** that direction (low/moderate/high).
- confidence: float in [0, 1] = certainty about this article's signal.
- Use only the literal strings shown for impact_strength, relevance, surprise, time_horizon (e.g. time_horizon \"1-3d\" exactly).
"""


def articles_dicts_to_payload(
    ticker: str,
    articles: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    ts = now or datetime.now(timezone.utc)
    batch_articles = []
    for i, a in enumerate(articles):
        summary = a.get("summary")
        if isinstance(summary, str):
            summary = summary.strip() or None
        src = a.get("publisher") or a.get("provider_id")
        batch_articles.append(
            {
                "article_index": i + 1,
                "title": (a.get("title") or "").strip(),
                "summary": summary,
                "timestamp": a.get("timestamp"),
                "source": src,
            }
        )
    return {
        "target_ticker": ticker.strip().upper(),
        "current_time": ts.isoformat(),
        "articles": batch_articles,
    }


def build_ollama_messages(
    ticker: str,
    articles: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> list[dict[str, str]]:
    if not articles:
        raise ValueError("articles must not be empty")
    payload = articles_dicts_to_payload(ticker, articles, now=now)
    core = USER_PROMPT_CORE.format(
        payload=json.dumps(payload, ensure_ascii=False, indent=2),
    )
    user = core + "\n\n" + OLLAMA_JSON_SUFFIX.format(schema_hint=SCHEMA_HINT)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]