#!/usr/bin/env bash
# Push в GitHub с PAT из слитого окружения: сначала tradenews/config.env, затем lse ../config.env
# (как with_tradenews_config_env.sh). Держите GITHUB_TOKEN один раз в lse/config.env — дублировать в tradenews не обязательно.
#
# Использование (из корня репозитория tradenews):
#   ./scripts/push_github_from_config_env.sh
#   ./scripts/push_github_from_config_env.sh origin main
#
# Аргументы: remote (по умолчанию origin), refspec (по умолчанию текущая ветка → та же ветка на remote).

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
  echo "push_github_from_config_env: нет ни $_LSE, ни $_LOCAL" >&2
  exit 1
fi

eval "$(python3 "$_TRADENEWS_ROOT/scripts/load_merged_tradenews_env.py" "$_LSE_ARG" "$_LOCAL_ARG")"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "push_github_from_config_env: GITHUB_TOKEN не задан (lse/config.env или tradenews/config.env)." >&2
  exit 1
fi

_REMOTE="${1:-origin}"
_BRANCH="${2:-}"
if [[ -z "$_BRANCH" ]]; then
  _BRANCH="$(git -C "$_TRADENEWS_ROOT" rev-parse --abbrev-ref HEAD)"
fi

_origin="$(git -C "$_TRADENEWS_ROOT" remote get-url "$_REMOTE")"
_repo_path=""
case "$_origin" in
  https://github.com/*)
    _repo_path="${_origin#https://github.com/}"
    ;;
  https://*@github.com/*)
    # уже с credentials — оставляем только host/path
    _repo_path="${_origin#*@github.com/}"
    ;;
  git@github.com:*)
    _repo_path="${_origin#git@github.com:}"
    ;;
  *)
    echo "push_github_from_config_env: неподдерживаемый URL remote $_REMOTE: $_origin" >&2
    exit 1
    ;;
esac

# GitHub рекомендует x-access-token как пользователя для PAT
_PUSH_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${_repo_path}"
unset GITHUB_TOKEN

cd "$_TRADENEWS_ROOT"
git push "$_PUSH_URL" "HEAD:refs/heads/${_BRANCH}"
