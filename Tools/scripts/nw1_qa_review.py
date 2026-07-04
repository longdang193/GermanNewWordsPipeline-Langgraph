#!/usr/bin/env python3
"""
NW1 QA gate: review Outputs/01_words.md for quality issues.

Default behavior: deterministic heuristic checks only.
Optional behavior: if pydantic-ai is installed and OPENAI_API_KEY is set,
can be extended to LLM review in later iteration.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from mdproc.validation_core import FieldLine, iter_blocks, iter_block_fields

ROOT = Path(__file__).resolve().parents[2]
TOOLS_SRC = ROOT / "Tools" / "src"
if str(TOOLS_SRC) not in sys.path:
    sys.path.insert(0, str(TOOLS_SRC))

from gnw_pipeline.llm_runtime import get_llm_runtime_settings  # noqa: E402
from gnw_pipeline.nw1_qa import (  # noqa: E402
    LlmIssueInput,
    QaEntry,
    QaIssue,
    any_fail,
    build_report_row,
    load_report_payload,
    normalize_llm_issue,
    qa_entry_from_fields,
    qa_entry_issues,
    write_report_payload,
)

try:
    from gnw_pipeline.nw1_llm_qa import llm_review_entry  # noqa: E402
except Exception:  # pragma: no cover
    llm_review_entry = None  # type: ignore[assignment]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NW1 QA review for Outputs/01_words.md")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repo root")
    parser.add_argument("--input", type=Path, default=Path("Outputs/01_words.md"))
    parser.add_argument("--output", type=Path, default=Path("Outputs/reports/nw1_qa_latest.json"))
    parser.add_argument("--fail-on-issues", action="store_true", help="Exit non-zero if issues found")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM QA via pydantic-ai (requires OPENAI_API_KEY and ai extra installed).",
    )
    parser.add_argument("--llm-model", default="openai:gpt-4.1-mini")
    return parser.parse_args()


def _entry_from_block(block_lines: list[FieldLine]) -> QaEntry | None:
    fields: dict[str, str] = {}
    for field in block_lines:
        field_name = getattr(field, "field_name")
        field_value = getattr(field, "field_value").strip()
        fields[field_name] = field_value
    return qa_entry_from_fields(fields)


async def _llm_issues_for_entry(entry: QaEntry, model: str) -> list[QaIssue]:
    if llm_review_entry is None:
        return []
    if not (entry.word and entry.meaning and entry.en_1 and entry.word_inf):
        return []

    result = await llm_review_entry(
        word=entry.word,
        meaning=entry.meaning,
        de_1=entry.de_1,
        en_1=entry.en_1,
        word_inf=entry.word_inf,
        model=model,
    )
    return [
        normalize_llm_issue(
            LlmIssueInput(
                code=issue.code,
                field=issue.field,
                severity=issue.severity,
                message=issue.message,
                evidence=issue.evidence,
            )
        )
        for issue in result.issues
    ]


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    input_path = (root / args.input).resolve()
    output_path = (root / args.output).resolve()

    if not input_path.exists():
        print(f"[ERROR] Missing input file: {input_path}")
        return 2

    llm_settings = None
    if args.llm:
        llm_settings = get_llm_runtime_settings(root=root, require_api_key=False)

    lines = input_path.read_text(encoding="utf-8", errors="replace").splitlines()
    existing_payload = load_report_payload(output_path)
    issue_rows = []

    for block in iter_blocks(lines):
        block_fields = list(iter_block_fields(block))
        entry = _entry_from_block(block_fields)
        if entry is None:
            continue

        deterministic_issues = qa_entry_issues(entry)
        llm_issues: list[QaIssue] = []
        if args.llm and llm_settings is not None and llm_settings.api_key:
            llm_issues = asyncio.run(_llm_issues_for_entry(entry, args.llm_model))

        if deterministic_issues or llm_issues:
            issue_rows.append(
                build_report_row(
                    entry=entry,
                    start_line=block.start_line,
                    end_line=block.end_line,
                    deterministic_issues=deterministic_issues,
                    llm_issues=llm_issues,
                )
            )

    env = dict(existing_payload["env"])
    env.update(
        {
            "report_stage": "nw1_qa_review",
            "openai_api_key_present": bool(llm_settings.api_key) if llm_settings is not None else False,
            "input": str(input_path),
        }
    )
    write_report_payload(
        output_path,
        results=tuple(existing_payload["results"]),
        issue_rows=issue_rows,
        env=env,
    )

    issue_count = sum(len(row.issues) for row in issue_rows)
    if issue_count:
        print(f"[WARN] NW1 QA found {issue_count} issues. Report: {output_path}")
        if args.fail_on_issues:
            all_issues = [issue for row in issue_rows for issue in row.issues]
            if any_fail(all_issues):
                return 1
    else:
        print(f"[OK] NW1 QA: no issues found. Report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
