#!/usr/bin/env bash
# git push в origin по HTTPS, подставляя GITHUB_TOKEN (без source всего config в bash).
#
# Порядок поиска GITHUB_TOKEN:
#   1) TRADENEWS_CONFIG_ENV (если задан и файл есть)
#   2) tradenews/config.env
#   3) LSE_CONFIG_ENV (если задан)
#   4) ../config.env от корня tradenews (проект lse)
#
#   cd tradenews
#   ./scripts/push_github_from_config_env.sh
#   ./scripts/push_github_from_config_env.sh main
#
# Права токена: минимум repo для приватного репозитория.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_LSE="${LSE_CONFIG_ENV:-$ROOT/../config.env}"
_LOCAL="${TRADENEWS_CONFIG_ENV:-$ROOT/config.env}"
BRANCH="${1:-$(git -C "$ROOT" branch --show-current)}"

TOKEN=""
_try_token() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  TOKEN="$(python3 "$ROOT/scripts/read_lse_config_key.py" "$f" GITHUB_TOKEN 2>/dev/null)" && return 0
  return 1
}

if [[ -n "${TRADENEWS_CONFIG_ENV:-}" ]]; then _try_token "$TRADENEWS_CONFIG_ENV" || true; fi
if [[ -z "$TOKEN" ]]; then _try_token "$_LOCAL" || true; fi
if [[ -z "$TOKEN" ]]; then _try_token "$_LSE" || true; fi
if [[ -z "$TOKEN" ]]; then
  echo "push_github_from_config_env: GITHUB_TOKEN не найден. Проверьте (по порядку):" >&2
  echo "  TRADENEWS_CONFIG_ENV=${TRADENEWS_CONFIG_ENV:-<unset>}" >&2
  echo "  $_LOCAL" >&2
  echo "  $_LSE" >&2
  exit 1
fi
ORIGIN="$(git -C "$ROOT" remote get-url origin)"

if [[ "$ORIGIN" != https://github.com/* && "$ORIGIN" != https://www.github.com/* ]]; then
  echo "push_github_from_config_env: origin должен быть HTTPS URL github.com, сейчас: $ORIGIN" >&2
  exit 1
fi

# https://github.com/owner/repo.git -> https://oauth2:TOKEN@github.com/owner/repo.git
HOSTPATH="${ORIGIN#https://}"
HOSTPATH="${HOSTPATH#www.}"
PUSH_URL="https://oauth2:${TOKEN}@${HOSTPATH}"

exec git -C "$ROOT" push "$PUSH_URL" "$BRANCH"
