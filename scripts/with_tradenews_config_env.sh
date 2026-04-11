#!/usr/bin/env bash
# Подхват переменных для tradenews: локальный config.env перекрывает lse (как load_merged_tradenews_env.py).
#
# Локальный файл (не в git): tradenews/config.env — см. config.env.example
#   cp config.env.example config.env
#
# Пути:
#   TRADENEWS_CONFIG_ENV — явный путь к локальному config (по умолчанию tradenews/config.env)
#   LSE_CONFIG_ENV — lse (по умолчанию ../config.env от корня tradenews)
#
# Пример:
#   ./scripts/with_tradenews_config_env.sh bash -c 'PYTHONPATH=. python scripts/run_openai_predict_fixture.py ...'
#
# Только lse без локального файла — эквивалентно with_lse_config_env.sh (если config.env нет).

set -euo pipefail
_TRADENEWS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_LSE="${LSE_CONFIG_ENV:-$_TRADENEWS_ROOT/../config.env}"
_LOCAL="${TRADENEWS_CONFIG_ENV:-$_TRADENEWS_ROOT/config.env}"

_LSE_ARG=""
if [[ -f "$_LSE" ]]; then
  _LSE_ARG="$_LSE"
fi
_LOCAL_ARG=""
if [[ -f "$_LOCAL" ]]; then
  _LOCAL_ARG="$_LOCAL"
fi
if [[ -z "$_LSE_ARG" && -z "$_LOCAL_ARG" ]]; then
  echo "with_tradenews_config_env: нет ни $_LSE, ни $_LOCAL" >&2
  echo "Создайте tradenews/config.env (см. config.env.example) и/или lse config.env." >&2
  exit 1
fi

eval "$(python3 "$_TRADENEWS_ROOT/scripts/load_merged_tradenews_env.py" "$_LSE_ARG" "$_LOCAL_ARG")"
cd "$_TRADENEWS_ROOT"
exec "$@"
