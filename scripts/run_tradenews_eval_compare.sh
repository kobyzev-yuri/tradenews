#!/usr/bin/env bash
# Запуск оценки Ollama по JSONL точкам и печать метрик (bias vs forward log-returns).
# Много горизонтов + JSON-отчёт: scripts/run_model_benchmark.py (см. --help).
#
# Из корня tradenews:
#   ./scripts/run_tradenews_eval_compare.sh
#   MAX_POINTS=5 ./scripts/run_tradenews_eval_compare.sh
#   STUB=1 ./scripts/run_tradenews_eval_compare.sh
# Только метрики по уже собранному JSONL:
#   SKIP_BUILD=1 OUT=runs/eval_lse_kb_400.jsonl ./scripts/run_tradenews_eval_compare.sh
#
# Переменные окружения (опционально):
#   PYTHON          — интерпретатор (по умолчанию python3)
#   POINTS_JSONL    — датасет точек
#   ARTICLES_BASE   — корень для articles_fixture_path
#   MODELS          — список моделей Ollama через пробел
#   OUT             — куда писать EvaluationRow JSONL
#   LOG             — полный лог (stdout+stderr прогона)
#   PROGRESS_JSON   — снимок прогресса для watch/tail
#   RUN_ID          — суффикс для OUT/LOG/PROGRESS, если OUT не задан
#   MAX_POINTS      — если задано, передаётся как --max-points
#   STUB            — 1 = без Ollama (--stub)
#   SKIP_BUILD      — 1 = не вызывать build_eval, только run_compare
#   OLLAMA_KEEP_ALIVE — например 30m или -1 (экспорт в среду для ollama_client)
#   RETURN_COL      — forward_log_return_1d | forward_log_return_3d | forward_log_return_5d
#   COMPARE_ALL_HORIZONS — 1 = после прогона напечатать сводки для 1d, 3d и 5d

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
export PYTHONUNBUFFERED=1

: "${PYTHON:=python3}"
: "${POINTS_JSONL:=datasets/points/lse_kb_per_row_equities.jsonl}"
: "${ARTICLES_BASE:=datasets}"
: "${MODELS:=llama3.2:3b qwen2.5:7b}"
: "${RUN_ID:=$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ -z "${OUT:-}" ]]; then
  OUT="runs/eval_${RUN_ID}.jsonl"
fi
if [[ -z "${LOG:-}" ]]; then
  LOG="runs/eval_${RUN_ID}.log"
fi
if [[ -z "${PROGRESS_JSON:-}" ]]; then
  PROGRESS_JSON="runs/eval_${RUN_ID}.progress.json"
fi
: "${RETURN_COL:=forward_log_return_1d}"
: "${OLLAMA_KEEP_ALIVE:=30m}"
export OLLAMA_KEEP_ALIVE

read -r -a MODEL_ARR <<< "${MODELS}"

SKIP_BUILD="${SKIP_BUILD:-0}"
STUB_FLAG=()
if [[ "${STUB:-0}" == "1" ]]; then
  STUB_FLAG=(--stub)
fi
MAX_FLAG=()
if [[ -n "${MAX_POINTS:-}" ]]; then
  MAX_FLAG=(--max-points "${MAX_POINTS}")
fi

mkdir -p runs

if [[ "$SKIP_BUILD" != "1" ]]; then
  echo "=== tradenews eval: $(date -Is) ===" | tee "$LOG"
  echo "ROOT=$ROOT PYTHON=$PYTHON" | tee -a "$LOG"
  echo "POINTS_JSONL=$POINTS_JSONL ARTICLES_BASE=$ARTICLES_BASE" | tee -a "$LOG"
  echo "MODELS=${MODEL_ARR[*]} OUT=$OUT" | tee -a "$LOG"
  echo "PROGRESS_JSON=$PROGRESS_JSON OLLAMA_KEEP_ALIVE=$OLLAMA_KEEP_ALIVE" | tee -a "$LOG"
  set +e
  "$PYTHON" -u scripts/build_eval_from_points.py \
    "$POINTS_JSONL" \
    --articles-base "$ARTICLES_BASE" \
    --models "${MODEL_ARR[@]}" \
    --out "$OUT" \
    --progress-json "$PROGRESS_JSON" \
    "${STUB_FLAG[@]}" \
    "${MAX_FLAG[@]}" \
    2>&1 | tee -a "$LOG"
  build_status="${PIPESTATUS[0]}"
  set -e
  if [[ "$build_status" -ne 0 ]]; then
    echo "build_eval_from_points.py exited with $build_status" | tee -a "$LOG"
    exit "$build_status"
  fi
else
  echo "SKIP_BUILD=1 — пропуск сборки, метрики по OUT=$OUT" | tee -a "${LOG:-/dev/stderr}"
fi

if [[ ! -f "$OUT" ]]; then
  echo "Нет файла $OUT — нечего сравнивать." >&2
  exit 1
fi

_run_compare() {
  local col="$1"
  echo "" | tee -a "$LOG"
  echo "--- metrics: $col ($(date -Is)) ---" | tee -a "$LOG"
  "$PYTHON" scripts/run_compare.py "$OUT" --return-col "$col" 2>&1 | tee -a "$LOG"
}

if [[ "${COMPARE_ALL_HORIZONS:-0}" == "1" ]]; then
  _run_compare forward_log_return_1d
  _run_compare forward_log_return_3d
  _run_compare forward_log_return_5d
else
  _run_compare "$RETURN_COL"
fi

echo "" | tee -a "$LOG"
echo "=== done: $(date -Is) OUT=$OUT LOG=$LOG ===" | tee -a "$LOG"
