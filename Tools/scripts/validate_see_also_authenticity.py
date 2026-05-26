#!/usr/bin/env python3
"""
@meta
name: validate_see_also_authenticity
type: script
domain: german-new-words
responsibility:
  - Detect synthetic or placeholder NID patterns in see_also entries.
  - Report suspicious consecutive numeric runs and uniform fake prefixes.
inputs:
  - Outputs/04_see_also.md
  - Outputs/05_see_also_fixed.md
  - Outputs/06_words_final.md
outputs:
  - Console report and non-zero exit code for suspicious patterns.
tags:
  - validation
  - see_also
  - nid
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


BLOCK_START = "SSTART"
BLOCK_END = "EEND"
NID_ENTRY_RE = re.compile(r"\[([^|\]]+)\|nid(\d+)\]")
FIELD_LINE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*:")

DEFAULT_FILES = (
    Path("Outputs/06_words_final.md"),
    Path("Outputs/05_see_also_fixed.md"),
    Path("Outputs/04_see_also.md"),
)
DEFAULT_NOTEBOOK_NAME = "Comprehensive German Language Learning and Vocabulary Guide"

SYNTHETIC_PREFIX = "1000000000"
MIN_BLOCK_SEQUENCE_LEN = 2
MIN_GLOBAL_SEQUENCE_LEN = 4
MIN_PREFIX_HIT_COUNT = 3


@dataclass(frozen=True)
class NidRecord:
    line_number: int
    base_word: str
    related_term: str
    nid_value: int


@dataclass(frozen=True)
class SequenceRun:
    length: int
    start_line: int
    end_line: int
    start_nid: int
    end_nid: int


def resolve_input_path(optional_input: str | None) -> Path | None:
    if optional_input:
        candidate = Path(optional_input)
        return candidate if candidate.exists() else None

    for candidate in DEFAULT_FILES:
        if candidate.exists():
            return candidate
    return None


def iter_blocks(lines: list[str]) -> Iterable[tuple[int, int, list[str]]]:
    index = 0
    while index < len(lines):
        if lines[index].strip() != BLOCK_START:
            index += 1
            continue

        start = index
        end = index + 1
        while end < len(lines) and lines[end].strip() != BLOCK_END:
            end += 1

        if end >= len(lines):
            return

        yield start, end, lines[start: end + 1]
        index = end + 1


def extract_word(block_lines: list[str]) -> str:
    for raw in block_lines:
        stripped = raw.strip()
        if stripped.lower().startswith("word:"):
            return stripped.split(":", 1)[1].strip()
    return "<unknown>"


def parse_nid_records(lines: list[str]) -> list[NidRecord]:
    records: list[NidRecord] = []

    for block_start, _block_end, block in iter_blocks(lines):
        base_word = extract_word(block)
        in_see_also = False

        for offset, raw in enumerate(block[1:-1], 1):
            line_number = block_start + offset + 1
            stripped = raw.strip()

            if stripped == "see_also:":
                in_see_also = True
                continue

            if in_see_also and stripped and FIELD_LINE_RE.match(stripped):
                in_see_also = False

            if not in_see_also:
                continue

            for term, nid in NID_ENTRY_RE.findall(stripped):
                records.append(
                    NidRecord(
                        line_number=line_number,
                        base_word=base_word,
                        related_term=term,
                        nid_value=int(nid),
                    )
                )

    return records


def find_consecutive_runs(records: list[NidRecord], minimum_len: int) -> list[SequenceRun]:
    if not records:
        return []

    runs: list[SequenceRun] = []
    run_start = records[0]
    previous = records[0]
    run_length = 1

    for current in records[1:]:
        if current.nid_value == previous.nid_value + 1:
            run_length += 1
            previous = current
            continue

        if run_length >= minimum_len:
            runs.append(
                SequenceRun(
                    length=run_length,
                    start_line=run_start.line_number,
                    end_line=previous.line_number,
                    start_nid=run_start.nid_value,
                    end_nid=previous.nid_value,
                )
            )

        run_start = current
        previous = current
        run_length = 1

    if run_length >= minimum_len:
        runs.append(
            SequenceRun(
                length=run_length,
                start_line=run_start.line_number,
                end_line=previous.line_number,
                start_nid=run_start.nid_value,
                end_nid=previous.nid_value,
            )
        )

    return runs


def detect_prefix_hits(records: list[NidRecord], prefix: str) -> list[NidRecord]:
    return [record for record in records if str(record.nid_value).startswith(prefix)]


def print_summary(path: Path, records: list[NidRecord]) -> None:
    print(f"[INFO] Authenticity validation target: {path}")
    print("=" * 60)
    print(f"Total see_also NIDs: {len(records)}")


def print_notebooklm_mcp_guidance(notebook_name: str, reason: str) -> None:
    print("[ACTION] Retrieve real see_also data via NotebookLM MCP.")
    print(f"[ACTION] Notebook: {notebook_name}")
    print(f"[ACTION] Reason: {reason}")
    print("[ACTION] Replace Outputs/04_see_also.md with NotebookLM MCP output before NW3/NW4.")


def validate(records: list[NidRecord]) -> tuple[list[str], list[str]]:
    hard_fail_issues: list[str] = []
    warning_issues: list[str] = []

    prefix_hits = detect_prefix_hits(records, SYNTHETIC_PREFIX)
    if len(prefix_hits) >= MIN_PREFIX_HIT_COUNT:
        hard_fail_issues.append(
            f"Detected {len(prefix_hits)} NIDs starting with '{SYNTHETIC_PREFIX}' (likely synthetic placeholders)."
        )

    global_runs = find_consecutive_runs(records, MIN_GLOBAL_SEQUENCE_LEN)
    if global_runs:
        example = global_runs[0]
        hard_fail_issues.append(
            "Detected long global consecutive NID run: "
            f"nid{example.start_nid}..nid{example.end_nid} "
            f"(length={example.length}, lines {example.start_line}-{example.end_line})."
        )

    grouped_by_word: dict[str, list[NidRecord]] = {}
    for record in records:
        grouped_by_word.setdefault(record.base_word, []).append(record)

    for base_word, word_records in grouped_by_word.items():
        block_runs = find_consecutive_runs(
            word_records, MIN_BLOCK_SEQUENCE_LEN)
        if block_runs:
            example = block_runs[0]
            warning_issues.append(
                f"Word '{base_word}' has consecutive NIDs "
                f"nid{example.start_nid}..nid{example.end_nid} "
                f"(length={example.length}, lines {example.start_line}-{example.end_line})."
            )

    return hard_fail_issues, warning_issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate see_also NIDs for synthetic/artificial numbering patterns."
    )
    parser.add_argument(
        "--input",
        help="Path to the markdown file to validate (defaults to final outputs in priority order).",
    )
    parser.add_argument(
        "--notebook-name",
        default=DEFAULT_NOTEBOOK_NAME,
        help="NotebookLM notebook name used as real-data source for see_also retrieval.",
    )
    args = parser.parse_args()

    target_path = resolve_input_path(args.input)
    if target_path is None:
        print("[ERROR] No input file found. Pass --input or generate Outputs first.")
        return 1

    content = target_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    records = parse_nid_records(lines)

    print_summary(target_path, records)

    if not records:
        print("[OK] No see_also NIDs found; nothing to validate.")
        print_notebooklm_mcp_guidance(
            args.notebook_name,
            "no see_also NIDs were found; real references are required",
        )
        return 0

    hard_fail_issues, warning_issues = validate(records)

    if warning_issues:
        print("[WARN] Suspicion hints:")
        for issue in warning_issues:
            print(f"  - {issue}")

    if hard_fail_issues:
        print("[FAIL] Artificial NID patterns detected:")
        for issue in hard_fail_issues:
            print(f"  - {issue}")
        print_notebooklm_mcp_guidance(
            args.notebook_name,
            "synthetic placeholder patterns were detected",
        )
        return 1

    print("[OK] No strong artificial NID patterns detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
