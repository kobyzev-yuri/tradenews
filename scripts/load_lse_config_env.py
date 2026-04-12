#!/usr/bin/env python3
"""Emit shell `export KEY='value'` for whitelisted keys from config.env (dotenv-like).

config.env is often not valid bash (unquoted colons, stray lines). Do not `source` it whole.

Ключи — ``tradenews.config_env.TRADENEWS_CONFIG_ENV_KEYS`` (единый список с load_merged_tradenews_env).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.config_env import parse_env_file, shell_single_quote


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: load_lse_config_env.py /path/to/config.env", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"load_lse_config_env: not a file: {path}", file=sys.stderr)
        return 1
    vals = parse_env_file(path)
    for key in sorted(vals):
        print(f"export {key}={shell_single_quote(vals[key])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
