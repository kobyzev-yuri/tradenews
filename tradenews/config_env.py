"""Загрузка whitelisted ключей из ``tradenews/config.env`` и ``lse/config.env`` (как ``load_merged_tradenews_env.py``).

Скрипты вроде ``python scripts/run_model_benchmark.py`` не проходят через
``with_tradenews_config_env.sh`` — без явного вызова ``apply_default_tradenews_env()``
переменные из файлов не попадут в ``os.environ``.
"""

from __future__ import annotations

import os
from pathlib import Path

# Синхронизировать с scripts/load_lse_config_env.py (комментарий там).
TRADENEWS_CONFIG_ENV_KEYS = frozenset(
    {
        "OPENAI_API_KEY",
        "OPENAI_GPT_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_TIMEOUT",
        "PROXYAPI_KEY",
        "TRADENEWS_PROXYAPI_KEY",
        "PROXYAPI_TIMEOUT",
        "TRADENEWS_USE_PROXYAPI",
        "TRADENEWS_OPENAI_COMPAT_BASE_URL",
        "TRADENEWS_PROXYAPI_DEEPSEEK_REASONER_MODEL",
        "TRADENEWS_PROXYAPI_DEEPSEEK_CHAT_MODEL",
        "TRADENEWS_OPENAI_MODEL",
        "TRADENEWS_EVAL_MODEL_SPECS",
        "TRADENEWS_OPENAI_JSON_OBJECT",
        "TRADENEWS_DEEPSEEK_JSON_OBJECT",
        "TRADENEWS_OPENAI_MAX_TOKENS",
        "TRADENEWS_OPENAI_MAX_TOKENS_PARAM",
        "OLLAMA_HOST",
        "OLLAMA_KEEP_ALIVE",
        "TRADENEWS_OLLAMA_MODELS",
        "TRADENEWS_OLLAMA_ARTICLES_JSON",
        "NYSE_PROJECT_ROOT",
        # PAT для git push (scripts/push_github_from_config_env.sh); как в lse/config.env.example
        "GITHUB_TOKEN",
    }
)


def tradenews_project_root() -> Path:
    """Корень пакета tradenews (родитель каталога ``tradenews`` с кодом)."""
    return Path(__file__).resolve().parent.parent


def shell_single_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def parse_env_file(path: Path) -> dict[str, str]:
    """Разбор одного ``config.env``: только ключи из ``TRADENEWS_CONFIG_ENV_KEYS``."""
    out: dict[str, str] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.startswith("\ufeff"):
        text = text[1:]
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip().lstrip("\ufeff")
        if key not in TRADENEWS_CONFIG_ENV_KEYS:
            continue
        val = rest.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def merged_env_tradenews(
    *,
    lse_config: Path | None,
    local_config: Path | None,
) -> dict[str, str]:
    """Локальный tradenews ``config.env`` перекрывает lse ``config.env``; пустые значения пропускаются."""
    lse_vals = parse_env_file(lse_config) if lse_config and lse_config.is_file() else {}
    loc_vals = parse_env_file(local_config) if local_config and local_config.is_file() else {}
    merged: dict[str, str] = {}
    for key in TRADENEWS_CONFIG_ENV_KEYS:
        val = loc_vals.get(key) or lse_vals.get(key)
        if val is None or val == "":
            continue
        merged[key] = val
    return merged


def shell_export_lines(merged: dict[str, str]) -> list[str]:
    return [f"export {k}={shell_single_quote(merged[k])}" for k in sorted(merged)]


def apply_default_tradenews_env(*, tradenews_root: Path | None = None) -> None:
    """Подставить в ``os.environ`` слитые значения из ``<lse>/config.env`` и ``<tradenews>/config.env``.

    Для каждого ключа: если в файлах после слияния значение непустое — записать в окружение
    (как при запуске через ``with_tradenews_config_env.sh``). Если в файлах пусто — существующее
    значение в ``os.environ`` не трогаем.
    """
    root = tradenews_root or tradenews_project_root()
    lse = root.parent / "config.env"
    loc = root / "config.env"
    merged = merged_env_tradenews(
        lse_config=lse if lse.is_file() else None,
        local_config=loc if loc.is_file() else None,
    )
    for k, v in merged.items():
        os.environ[k] = v
