"""
Конвертация выгрузки LSE ``knowledge_base`` (CSV) → ``DatasetPoint`` / JSONL.

Формат статьи в ``articles_snapshot`` совместим с nyse ``serialize_news_article`` / tradenews fixtures.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal, Optional

import pandas as pd

from tradenews.schemas import DatasetPoint

Mode = Literal["per_row", "daily"]


def parse_ts_utc(val: Any) -> datetime:
    """Приводит ts из CSV/pandas к aware UTC."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        raise ValueError("ts is null")
    if isinstance(val, pd.Timestamp):
        dt = val.to_pydatetime()
    else:
        s = str(val).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _sentiment_to_cheap(s: Any) -> Optional[float]:
    """LSE KB: sentiment_score 0..1 (0 негатив, 1 позитив) → cheap_sentiment -1..1."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    try:
        x = float(s)
    except (TypeError, ValueError):
        return None
    x = max(0.0, min(1.0, x))
    return round((x - 0.5) * 2.0, 4)


def kb_row_to_article(row: pd.Series) -> dict[str, Any]:
    """Одна строка knowledge_base → один dict статьи."""
    content = str(row.get("content") or "").strip()
    lines = [x.strip() for x in content.split("\n") if x.strip()]
    title = (lines[0][:500] if lines else "(empty)")
    summary = "\n".join(lines[1:])[:8000] if len(lines) > 1 else None

    ts = parse_ts_utc(row["ts"])
    ticker = str(row.get("ticker") or "").strip().upper()
    if not ticker:
        raise ValueError("empty ticker")

    link = row.get("link")
    if link is not None and isinstance(link, float) and pd.isna(link):
        link = None
    if link is not None:
        link = str(link).strip() or None

    src = row.get("source")
    if src is not None and isinstance(src, float) and pd.isna(src):
        src = None
    src = str(src).strip() if src else None

    return {
        "ticker": ticker,
        "title": title,
        "timestamp": ts.isoformat(),
        "summary": summary,
        "link": link,
        "publisher": src,
        "provider_id": "lse_kb",
        "raw_sentiment": None,
        "cheap_sentiment": _sentiment_to_cheap(row.get("sentiment_score")),
    }


def load_kb_csv(path: Path | str) -> pd.DataFrame:
    p = Path(path)
    return pd.read_csv(p, encoding="utf-8", engine="python", on_bad_lines="warn")


def iter_dataset_points_from_kb(
    df: pd.DataFrame,
    *,
    mode: Mode = "per_row",
    tickers: Optional[set[str]] = None,
    max_points: Optional[int] = None,
) -> Iterator[DatasetPoint]:
    """
    ``per_row`` — одна точка на строку KB (одна статья).
    ``daily`` — группировка по (ticker, календарный день UTC); ``decision_ts`` = max(ts) в группе.
    """
    if "ts" not in df.columns or "ticker" not in df.columns:
        raise ValueError("CSV must contain columns ts, ticker")

    df = df.copy()
    df = df[df["ts"].notna() & df["ticker"].notna()]
    if tickers is not None:
        df = df[df["ticker"].str.upper().isin(tickers)]

    n_out = 0
    if mode == "per_row":
        for _, row in df.iterrows():
            if max_points is not None and n_out >= max_points:
                break
            try:
                art = kb_row_to_article(row)
                ts = parse_ts_utc(row["ts"])
            except (ValueError, KeyError):
                continue
            et = row.get("event_type")
            event_tag = None if et is None or (isinstance(et, float) and pd.isna(et)) else str(et).strip() or None
            kid = row.get("id")
            notes = f"lse_kb_id={int(kid)}" if kid is not None and not pd.isna(kid) else "lse_kb"
            yield DatasetPoint(
                ticker=art["ticker"],
                decision_ts_utc=ts,
                articles_snapshot=[art],
                event_tag=event_tag,
                notes=notes,
            )
            n_out += 1
        return

    # daily
    df["_ts_utc"] = df.apply(lambda r: parse_ts_utc(r["ts"]), axis=1)
    df["_d"] = df["_ts_utc"].apply(lambda t: t.date())
    df["_tu"] = df["ticker"].str.strip().str.upper()
    for (ticker, _d), g in df.groupby(["_tu", "_d"], sort=True):
        if max_points is not None and n_out >= max_points:
            break
        arts: list[dict[str, Any]] = []
        ids: list[int] = []
        event_tags: set[str] = set()
        for _, row in g.iterrows():
            try:
                arts.append(kb_row_to_article(row))
                kid = row.get("id")
                if kid is not None and not pd.isna(kid):
                    ids.append(int(kid))
                et = row.get("event_type")
                if et is not None and not (isinstance(et, float) and pd.isna(et)):
                    t = str(et).strip()
                    if t:
                        event_tags.add(t)
            except (ValueError, KeyError):
                continue
        if not arts:
            continue
        decision_ts = max(parse_ts_utc(r["ts"]) for _, r in g.iterrows())
        tag = ",".join(sorted(event_tags)) if event_tags else None
        notes = f"lse_kb_ids={','.join(map(str, sorted(ids)[:50]))}"
        if len(ids) > 50:
            notes += ",…"
        yield DatasetPoint(
            ticker=str(ticker).upper(),
            decision_ts_utc=decision_ts,
            articles_snapshot=arts,
            event_tag=tag,
            notes=notes,
        )
        n_out += 1


def write_dataset_points_jsonl(points: Iterator[DatasetPoint], out_path: Path | str) -> int:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w", encoding="utf-8") as f:
        for pt in points:
            f.write(json.dumps(pt.to_json_dict(), ensure_ascii=False) + "\n")
            n += 1
    return n
