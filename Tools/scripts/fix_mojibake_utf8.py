#!/usr/bin/env python3
"""
Fix common UTF-8 mojibake in Markdown outputs.

This repairs cases where UTF-8 text was decoded as latin-1/cp1252 and then
re-encoded, producing sequences like:
  RÃ¼ckkehr -> Rückkehr

Strategy:
- Only attempt repair on lines that contain typical mojibake markers (Ã, Â).
- Try round-trip: bytes = line.encode('latin-1'), then decode('utf-8').
  If it fails, keep original line.
"""

from __future__ import annotations

import argparse
from pathlib import Path


MOJIBAKE_MARKERS = ("Ã", "Â")


def fix_line(line: str) -> str:
    if not any(m in line for m in MOJIBAKE_MARKERS):
        return line
    try:
        return line.encode("latin-1").decode("utf-8")
    except Exception:
        return line


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else in_path

    text = in_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=False)

    fixed_lines = [fix_line(ln) for ln in lines]
    fixed_text = "\n".join(fixed_lines) + ("\n" if text.endswith("\n") else "")

    out_path.write_text(fixed_text, encoding="utf-8", newline="\n")

    before = sum(1 for ln in lines if any(m in ln for m in MOJIBAKE_MARKERS))
    after = sum(1 for ln in fixed_lines if any(m in ln for m in MOJIBAKE_MARKERS))
    print(f"markers_before={before} markers_after={after} out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

