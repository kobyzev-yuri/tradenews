"""JSONL: одна строка JSON на EvaluationRow или DatasetPoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Union

from tradenews.schemas import EvaluationRow


def evaluation_row_jsonl_line(row: EvaluationRow) -> str:
    return json.dumps(row.to_json_dict(), ensure_ascii=False) + "\n"


def write_evaluation_rows(path: Path | str, rows: list[EvaluationRow]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(evaluation_row_jsonl_line(r))


def read_evaluation_rows(path: Path | str) -> list[EvaluationRow]:
    p = Path(path)
    out: list[EvaluationRow] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(EvaluationRow.from_json_dict(json.loads(line)))
    return out


def iter_evaluation_rows(path: Path | str) -> Iterator[EvaluationRow]:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield EvaluationRow.from_json_dict(json.loads(line))
