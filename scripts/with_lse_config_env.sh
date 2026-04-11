#!/usr/bin/env bash
# Подхватить ключи и URL из config.env корня lse (рядом с каталогом tradenews), затем выполнить команду из tradenews.
#
#   cd tradenews
#   ./scripts/with_lse_config_env.sh env | grep -E '^OPENAI'
#   ./scripts/with_lse_config_env.sh bash -c 'PYTHONUNBUFFERED=1 PYTHONPATH=. python scripts/build_eval_from_points.py \
#     datasets/points/example_mu.jsonl --models llama3.2:3b qwen2.5:7b openai:${OPENAI_MODEL} --out runs/eval_three.jsonl'
#   (bash -c нужен, чтобы OPENAI_MODEL раскрылся после подхвата config.env, а не в вашем текущем shell)
#   ./scripts/with_lse_config_env.sh PYTHONPATH=. python scripts/run_compare.py runs/eval_three.jsonl
#
# Другой путь к config.env:
#   export LSE_CONFIG_ENV=/home/you/lse/config.env
#   ./scripts/with_lse_config_env.sh ...

set -euo pipefail
_TRADENEWS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_LSE_CONFIG="${LSE_CONFIG_ENV:-$_TRADENEWS_ROOT/../config.env}"
if [[ ! -f "$_LSE_CONFIG" ]]; then
  echo "with_lse_config_env: не найден $_LSE_CONFIG" >&2
  echo "Задайте LSE_CONFIG_ENV=/абсолютный/путь/config.env или положите lse/config.env на уровень выше tradenews/." >&2
  exit 1
fi
# Не source весь config.env: файл может содержать строки, невалидные для bash.
# Подхватываем только переменные tradenews (см. scripts/load_lse_config_env.py).
eval "$(python3 "$_TRADENEWS_ROOT/scripts/load_lse_config_env.py" "$_LSE_CONFIG")"
cd "$_TRADENEWS_ROOT"
exec "$@"
