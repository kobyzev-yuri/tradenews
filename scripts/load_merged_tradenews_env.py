#!/usr/bin/env python3
"""Печатает export для whitelisted ключей: локальный tradenews/config.env перекрывает lse config.env.

Первый аргумент — путь к lse (может отсутствовать: тогда пустая строка).
Второй — локальный tradenews (может отсутствовать: пустая строка).
Нужен хотя бы один существующий файл.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Синхронизировать с scripts/load_lse_config_env.py
_KEYS = frozenset(
    {
        "OPENAI_API_KEY",
        "OPENAI_GPT_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_TIMEOUT",
        "TRADENEWS_OPENAI_MODEL",
        "TRADENEWS_OPENAI_JSON_OBJECT",
        "TRADENEWS_OPENAI_MAX_TOKENS",
        "TRADENEWS_OPENAI_MAX_TOKENS_PARAM",
        "OLLAMA_HOST",
        "OLLAMA_KEEP_ALIVE",
        "TRADENEWS_OLLAMA_MODELS",
        "TRADENEWS_OLLAMA_ARTICLES_JSON",
        "NYSE_PROJECT_ROOT",
    }
)


def _shell_single_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _parse(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        if key not in _KEYS:
            continue
        val = rest.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: load_merged_tradenews_env.py LSE_CONFIG_PATH TRADENEWS_LOCAL_CONFIG_PATH",
            file=sys.stderr,
        )
        print("  use empty string for a missing file", file=sys.stderr)
        return 2
    lse_s, loc_s = sys.argv[1].strip(), sys.argv[2].strip()
    lse_p = Path(lse_s) if lse_s else None
    loc_p = Path(loc_s) if loc_s else None
    lse_vals = _parse(lse_p) if lse_p and lse_p.is_file() else {}
    loc_vals = _parse(loc_p) if loc_p and loc_p.is_file() else {}
    if not lse_vals and not loc_vals:
        print("load_merged_tradenews_env: ни один файл не найден или в них нет whitelisted ключей", file=sys.stderr)
        return 1
    for key in sorted(_KEYS):
        val = loc_vals.get(key) or lse_vals.get(key)
        if val is None or val == "":
            continue
        print(f"export {key}={_shell_single_quote(val)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
