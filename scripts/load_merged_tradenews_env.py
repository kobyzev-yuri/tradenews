#!/usr/bin/env python3
"""Печатает export для whitelisted ключей: локальный tradenews/config.env перекрывает lse config.env.

Первый аргумент — путь к lse (может отсутствовать: тогда пустая строка).
Второй — локальный tradenews (может отсутствовать: пустая строка).
Нужен хотя бы один существующий файл.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tradenews.config_env import merged_env_tradenews, shell_export_lines


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
    lse_f = lse_p if (lse_p and lse_p.is_file()) else None
    loc_f = loc_p if (loc_p and loc_p.is_file()) else None
    if not lse_f and not loc_f:
        print("load_merged_tradenews_env: ни один файл не найден", file=sys.stderr)
        return 1
    merged = merged_env_tradenews(lse_config=lse_f, local_config=loc_f)
    if not merged:
        print(
            "load_merged_tradenews_env: в файлах нет whitelisted ключей (см. tradenews.config_env)",
            file=sys.stderr,
        )
        return 1
    for line in shell_export_lines(merged):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
