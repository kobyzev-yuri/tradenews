"""
Паритет промпта L5 с репозиторием nyse (рядом с lse: ``lse/nyse`` → checkout).

Пропускается, если nyse не смонтирован — CI без полного nyse не ломается.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TRADENEWS_ROOT = Path(__file__).resolve().parent.parent
_LSE_ROOT = _TRADENEWS_ROOT.parent
_NYSE_ROOT = _LSE_ROOT / "nyse"


def _nyse_importable() -> bool:
    r = _NYSE_ROOT.resolve()
    return (r / "domain.py").is_file() and (r / "pipeline" / "news" / "news_signal_prompt.py").is_file()


@pytest.mark.skipif(not _nyse_importable(), reason="nyse repo not found at lse/nyse (symlink or clone)")
def test_system_prompt_matches_nyse() -> None:
    root = str(_NYSE_ROOT.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)

    from pipeline.news import news_signal_prompt as nsp

    from tradenews.prompt_news_signal import PROMPT_VERSION, SYSTEM_PROMPT

    assert SYSTEM_PROMPT == nsp.SYSTEM_PROMPT
    assert PROMPT_VERSION == nsp.PROMPT_VERSION


@pytest.mark.skipif(not _nyse_importable(), reason="nyse repo not found at lse/nyse")
def test_user_prompt_core_matches_nyse_template() -> None:
    root = str(_NYSE_ROOT.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)

    from pipeline.news import news_signal_prompt as nsp

    from tradenews.prompt_news_signal import USER_PROMPT_CORE

    assert USER_PROMPT_CORE.strip() == nsp.USER_PROMPT_TEMPLATE.strip()
