"""Сериализуемые контракты для датасета и строк оценки."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class DatasetPoint:
    """
    Одна точка для прогона предиктора.

    ``decision_ts_utc`` — момент «решения»: новости и цены *до* него входят в predict;
    forward return считается *после* (см. valuation).
    """

    ticker: str
    decision_ts_utc: datetime
    # Опционально: снимок статей (список dict как из nyse / JSON dump) для реплея разных моделей.
    articles_snapshot: Optional[list[dict[str, Any]]] = None
    # Опционально: путь к JSON-массиву статей (относительно --articles-base или файла датасета).
    articles_fixture_path: Optional[str] = None
    # Опционально: сохранённый тех. bias для будущего fusion-слоя
    tech_bias: Optional[float] = None
    # Разметка сценария (гео, ФРС, …) — попадает в EvaluationRow.extra
    event_tag: Optional[str] = None
    notes: Optional[str] = None

    def to_json_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["decision_ts_utc"] = self.decision_ts_utc.isoformat()
        return d

    @classmethod
    def from_json_dict(cls, d: dict[str, Any]) -> DatasetPoint:
        ts = d["decision_ts_utc"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return cls(
            ticker=d["ticker"],
            decision_ts_utc=ts,
            articles_snapshot=d.get("articles_snapshot"),
            articles_fixture_path=d.get("articles_fixture_path"),
            tech_bias=d.get("tech_bias"),
            event_tag=d.get("event_tag"),
            notes=d.get("notes"),
        )


@dataclass
class EvaluationRow:
    """
    Одна строка для метрик: predict + val + идентификация модели.

    Поля ``forward_log_return_*`` могут быть заполнены постфактум valuation-слоем.
    """

    ticker: str
    decision_ts_utc: datetime
    model_id: str

    bias_predict: float
    confidence_predict: Optional[float] = None

    forward_log_return_1d: Optional[float] = None
    forward_log_return_3d: Optional[float] = None
    forward_log_return_5d: Optional[float] = None

    llm_mode: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ticker": self.ticker,
            "decision_ts_utc": self.decision_ts_utc.isoformat(),
            "model_id": self.model_id,
            "bias_predict": self.bias_predict,
            "confidence_predict": self.confidence_predict,
            "forward_log_return_1d": self.forward_log_return_1d,
            "forward_log_return_3d": self.forward_log_return_3d,
            "forward_log_return_5d": self.forward_log_return_5d,
            "llm_mode": self.llm_mode,
        }
        d.update(self.extra)
        return d

    @classmethod
    def from_json_dict(cls, d: dict[str, Any]) -> EvaluationRow:
        ts = d["decision_ts_utc"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        extra = {k: v for k, v in d.items() if k not in _EVAL_FIELDS}
        return cls(
            ticker=d["ticker"],
            decision_ts_utc=ts,
            model_id=d["model_id"],
            bias_predict=float(d["bias_predict"]),
            confidence_predict=_opt_float(d.get("confidence_predict")),
            forward_log_return_1d=_opt_float(d.get("forward_log_return_1d")),
            forward_log_return_3d=_opt_float(d.get("forward_log_return_3d")),
            forward_log_return_5d=_opt_float(d.get("forward_log_return_5d")),
            llm_mode=d.get("llm_mode"),
            extra=extra,
        )


_EVAL_FIELDS = frozenset(
    {
        "ticker",
        "decision_ts_utc",
        "model_id",
        "bias_predict",
        "confidence_predict",
        "forward_log_return_1d",
        "forward_log_return_3d",
        "forward_log_return_5d",
        "llm_mode",
    }
)


def _opt_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    return float(x)
