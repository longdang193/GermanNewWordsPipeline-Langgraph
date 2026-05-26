#!/usr/bin/env python3
"""Repair malformed SSTART...EEND block structure in markdown vocabulary files.

This script focuses on structural integrity only:
- Ensures every block starts with SSTART and ends with EEND.
- Handles nested SSTART by closing the current block and starting a new one.
- Handles orphan field lines outside blocks by reattaching them to the latest block.
- Drops stray EEND lines outside blocks.

It does not attempt semantic/linguistic corrections.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*:")


def _block_body(block: list[str]) -> list[str]:
    return block[1:-1]


def _field_values(block: list[str], field_name: str) -> list[str]:
    prefix = f"{field_name}:"
    values: list[str] = []
    for raw in _block_body(block):
        stripped = raw.strip()
        if stripped.startswith(prefix):
            values.append(stripped.split(":", 1)[1].strip())
    return values


def _has_field(block: list[str], field_name: str) -> bool:
    return bool(_field_values(block, field_name))


def _has_see_also_entries(block: list[str]) -> bool:
    in_see_also = False
    for raw in _block_body(block):
        stripped = raw.strip()
        if stripped == "see_also:":
            in_see_also = True
            continue
        if in_see_also and FIELD_RE.match(stripped):
            in_see_also = False
        if in_see_also and stripped:
            return True
    return False


def _is_shell_block(block: list[str]) -> bool:
    # Typical split pattern: a block has only word/meaning and gets cut before details.
    return (
        _has_field(block, "word")
        and not _has_field(block, "word_inf")
        and not _has_field(block, "Tags")
        and not _has_see_also_entries(block)
    )


def _is_continuation_block(block: list[str]) -> bool:
    if _has_field(block, "word"):
        return False
    return (
        _has_field(block, "word_inf")
        or _has_field(block, "Tags")
        or _has_see_also_entries(block)
        or _has_field(block, "noun_gender")
        or _has_field(block, "noun_genetiv")
        or _has_field(block, "noun_plural")
        or _has_field(block, "verb_present")
        or _has_field(block, "verb_past")
        or _has_field(block, "verb_perfect")
    )


def _merge_pair(shell: list[str], continuation: list[str]) -> list[str]:
    merged_body: list[str] = []
    seen_vocab = False

    for raw in [*_block_body(shell), *_block_body(continuation)]:
        stripped = raw.strip()
        if stripped == "%VOCAB (German) ver 3":
            if seen_vocab:
                continue
            seen_vocab = True
        merged_body.append(raw)

    return ["SSTART\n", *merged_body, "EEND\n"]


def merge_shell_continuations(blocks: list[list[str]]) -> tuple[list[list[str]], int]:
    merged_blocks: list[list[str]] = []
    merges = 0
    i = 0
    while i < len(blocks):
        if i + 1 < len(blocks) and _is_shell_block(blocks[i]) and _is_continuation_block(blocks[i + 1]):
            merged_blocks.append(_merge_pair(blocks[i], blocks[i + 1]))
            merges += 1
            i += 2
            continue
        merged_blocks.append(blocks[i])
        i += 1
    return merged_blocks, merges


def _is_header_line(stripped: str) -> bool:
    return stripped.startswith("TARGET DECK:") or stripped.startswith("<!--")


def _is_payload_line(stripped: str) -> bool:
    if not stripped:
        return False
    if stripped in {"SSTART", "EEND"}:
        return False
    if stripped == "%VOCAB (German) ver 3":
        return True
    if stripped == "see_also:":
        return True
    if stripped.startswith("[") or stripped.startswith("der [") or stripped.startswith("die [") or stripped.startswith("das ["):
        return True
    return bool(FIELD_RE.match(stripped))


def _finalize_block(block: list[str], blocks: list[list[str]]) -> None:
    cleaned: list[str] = []
    for line in block:
        stripped = line.strip()
        if stripped in {"SSTART", "EEND"}:
            continue
        cleaned.append(line)

    normalized = ["SSTART\n", *cleaned, "EEND\n"]
    blocks.append(normalized)


def repair_structure(lines: list[str]) -> tuple[list[str], dict[str, int]]:
    output_prefix: list[str] = []
    blocks: list[list[str]] = []

    current: list[str] | None = None
    first_block_seen = False

    stats = {
        "nested_starts": 0,
        "stray_ends": 0,
        "orphan_payload_lines": 0,
        "implicit_block_starts": 0,
    }

    def start_block() -> None:
        nonlocal current, first_block_seen
        current = ["SSTART\n"]
        first_block_seen = True

    for raw in lines:
        stripped = raw.strip()

        if stripped == "SSTART":
            if current is not None:
                stats["nested_starts"] += 1
                _finalize_block(current, blocks)
            start_block()
            continue

        if stripped == "EEND":
            if current is None:
                stats["stray_ends"] += 1
                continue
            _finalize_block(current, blocks)
            current = None
            continue

        if current is not None:
            current.append(raw)
            continue

        # Outside block.
        if not first_block_seen and (_is_header_line(stripped) or not stripped):
            output_prefix.append(raw)
            continue

        if _is_payload_line(stripped):
            stats["orphan_payload_lines"] += 1
            if blocks:
                # Reopen previous block to absorb payload drift.
                reopened = blocks.pop()
                current = reopened[:-1]
                current.append(raw)
            else:
                stats["implicit_block_starts"] += 1
                start_block()
                current.append(raw)
            continue

        # Keep unknown non-payload lines in prefix only before first block, otherwise drop.
        if not first_block_seen:
            output_prefix.append(raw)

    if current is not None:
        _finalize_block(current, blocks)

    blocks, merges = merge_shell_continuations(blocks)

    repaired_lines = output_prefix[:]
    for block in blocks:
        repaired_lines.extend(block)
        if repaired_lines and repaired_lines[-1].strip():
            repaired_lines.append("\n")

    # Remove trailing blank lines.
    while repaired_lines and not repaired_lines[-1].strip():
        repaired_lines.pop()
    repaired_lines.append("\n")

    stats["blocks"] = len(blocks)
    stats["merged_shell_blocks"] = merges
    return repaired_lines, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair broken SSTART...EEND block structure")
    parser.add_argument(
        "--input", default="Outputs/06_words_final.md", help="Input markdown file")
    parser.add_argument(
        "--output", default="Outputs/06_words_final_repaired.md", help="Output markdown file")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        print(f"[ERROR] Input file not found: {in_path}")
        return 1

    lines = in_path.read_text(encoding="utf-8").splitlines(keepends=True)
    repaired, stats = repair_structure(lines)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(repaired), encoding="utf-8")

    print(f"[OK] Repaired file written: {out_path}")
    print(f"[INFO] Blocks: {stats['blocks']}")
    print(f"[INFO] Nested SSTART handled: {stats['nested_starts']}")
    print(f"[INFO] Stray EEND removed: {stats['stray_ends']}")
    print(
        f"[INFO] Orphan payload lines reattached: {stats['orphan_payload_lines']}")
    print(f"[INFO] Implicit blocks started: {stats['implicit_block_starts']}")
    print(
        f"[INFO] Shell+continuation block merges: {stats['merged_shell_blocks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
