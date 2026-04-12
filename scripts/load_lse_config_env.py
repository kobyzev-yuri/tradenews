#!/usr/bin/env python3
"""Emit shell `export KEY='value'` for whitelisted keys from config.env (dotenv-like).

config.env is often not valid bash (unquoted colons, stray lines). Do not `source` it whole.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Keys tradenews / compare / fixtures read from the environment.
# Держите в синхроне с scripts/load_merged_tradenews_env.py
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


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: load_lse_config_env.py /path/to/config.env", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"load_lse_config_env: not a file: {path}", file=sys.stderr)
        return 1
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
        print(f"export {key}={_shell_single_quote(val)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
