"""
Опциональная связка с nyse: ``NYSE_PROJECT_ROOT`` в PYTHONPATH, затем
``run_news_signal_pipeline`` — для эталонного сравнения с прод-пайплайном.

Реализация отложена: требует статей ``NewsArticle``, гейта и конфига ``ThresholdConfig``.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from tradenews.predictors.base import NewsPrediction, NewsPredictor


def ensure_nyse_path() -> None:
    root = os.environ.get("NYSE_PROJECT_ROOT", "").strip()
    if not root:
        raise RuntimeError("Set NYSE_PROJECT_ROOT to the nyse repo root for NyseReferencePredictor.")
