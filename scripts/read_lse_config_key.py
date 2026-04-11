#!/usr/bin/env python3
"""Печатает значение одного ключа из dotenv-подобного файла (без source всего файла в bash)."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: read_lse_config_key.py /path/to/config.env KEY_NAME", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    want = sys.argv[2].strip()
    if not path.is_file():
        print(f"read_lse_config_key: not a file: {path}", file=sys.stderr)
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
        if key.strip() != want:
            continue
        val = rest.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if not val:
            print(f"read_lse_config_key: empty value for {want!r}", file=sys.stderr)
            return 1
        print(val, end="")
        return 0
    print(f"read_lse_config_key: key {want!r} not found in {path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
