#!/usr/bin/env bash
# После export_lse_gcp_kb_quotes.sh: собрать JSONL точек для игрового universe тикеров (метрики tradenews).
#
# Из каталога tradenews/:
#   ./scripts/build_game_dataset_from_kb_dump.sh
#
# Переменные окружения:
#   KB_CSV          — явный путь к knowledge_base_*.csv (иначе берётся самый новый в datasets/lse_gcp_dump/)
#   TICKERS_FILE    — default datasets/tickers_game_universe.txt
#   DATASET_MODE    — daily | per_row (default: daily — разумнее для LLM: пачка статей на (тикер, день))
#   MAX_POINTS      — лимит строк JSONL, 0 = без лимита
#   OUT_JSONL       — явный путь вывода (иначе datasets/points/lse_kb_game_${MODE}_${UTC_STAMP}.jsonl)
#
# Котировки: в том же прогоне export_lse_gcp_kb_quotes.sh уже создаётся quotes_last${DAYS}d_*.csv рядом с KB.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TFILE="${TICKERS_FILE:-$ROOT/datasets/tickers_game_universe.txt}"
if [[ ! -f "$TFILE" ]]; then
  echo "Нет файла тикеров: $TFILE" >&2
  exit 1
fi

if [[ -n "${KB_CSV:-}" ]]; then
  KB="$KB_CSV"
else
  KB="$(ls -t "$ROOT/datasets/lse_gcp_dump"/knowledge_base_last*.csv 2>/dev/null | head -1 || true)"
fi
if [[ -z "$KB" || ! -f "$KB" ]]; then
  echo "Нет CSV knowledge_base в datasets/lse_gcp_dump/. Из корня репозитория lse выполните:" >&2
  echo "  export SSH_TARGET=gcp-lse   # или user@host" >&2
  echo "  export DAYS=90" >&2
  echo "  ./scripts/export_lse_gcp_kb_quotes.sh" >&2
  exit 1
fi

TICKERS="$(
  python3 - <<PY
from pathlib import Path
p = Path(r"""$TFILE""")
order: list[str] = []
s: set[str] = set()
for raw in p.read_text(encoding="utf-8").splitlines():
    line = raw.split("#", 1)[0].strip()
    if not line:
        continue
    u = line.upper()
    if u not in s:
        s.add(u)
        order.append(u)
print(",".join(order))
PY
)"
if [[ -z "$TICKERS" ]]; then
  echo "Пустой список тикеров в $TFILE" >&2
  exit 1
fi

MODE="${DATASET_MODE:-daily}"
MAXPTS="${MAX_POINTS:-0}"
STAMP="$(date -u +%Y%m%d_%H%M%SZ)"
OUT="${OUT_JSONL:-$ROOT/datasets/points/lse_kb_game_${MODE}_${STAMP}.jsonl}"

echo "KB=$KB" >&2
echo "tickers=$(echo "$TICKERS" | tr ',' '\n' | wc -l) symbols" >&2
echo "OUT=$OUT mode=$MODE max_points=$MAXPTS" >&2

MAX_FLAG=()
if [[ "$MAXPTS" != "0" ]]; then
  MAX_FLAG=(--max-points "$MAXPTS")
fi

export PYTHONPATH="$ROOT"
python3 "$ROOT/scripts/lse_csv_to_dataset_points.py" \
  --kb "$KB" \
  --out "$OUT" \
  --mode "$MODE" \
  --tickers "$TICKERS" \
  "${MAX_FLAG[@]}"

QT="$(ls -t "$ROOT/datasets/lse_gcp_dump"/quotes_last*.csv 2>/dev/null | head -1 || true)"
if [[ -n "$QT" && -f "$QT" ]]; then
  echo "quotes_csv (рядом с дампом): $QT" >&2
else
  echo "Примечание: quotes_last*.csv не найден — перезапустите export_lse_gcp_kb_quotes.sh для котировок." >&2
fi

echo "Done: $OUT" >&2
