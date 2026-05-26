#!/usr/bin/env python3
"""
NW1 QA gate: review Outputs/01_words.md for quality issues.

Default behavior: deterministic heuristic checks only.
Optional behavior: if pydantic-ai is installed and OPENAI_API_KEY is set,
can be extended to LLM review in later iteration.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import asyncio
from dataclasses import asdict
from pathlib import Path

from mdproc.validation_core import iter_blocks, iter_block_fields

ROOT = Path(__file__).resolve().parents[2]
TOOLS_SRC = ROOT / "Tools" / "src"
if str(TOOLS_SRC) not in sys.path:
    sys.path.insert(0, str(TOOLS_SRC))

from gnw_pipeline.nw1_qa import qa_de1_issues, any_fail  # noqa: E402
try:
    from gnw_pipeline.nw1_llm_qa import llm_review_entry  # noqa: E402
except Exception:  # pragma: no cover
    llm_review_entry = None  # type: ignore[assignment]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NW1 QA review for Outputs/01_words.md")
    p.add_argument("--root", type=Path, default=Path("."), help="Repo root")
    p.add_argument("--input", type=Path, default=Path("Outputs/01_words.md"))
    p.add_argument("--output", type=Path, default=Path("Outputs/reports/nw1_qa_latest.json"))
    p.add_argument("--fail-on-issues", action="store_true", help="Exit non-zero if issues found")
    p.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM QA via pydantic-ai (requires OPENAI_API_KEY and ai extra installed).",
    )
    p.add_argument("--llm-model", default=os.environ.get("GNW_NW1_QA_MODEL", "openai:gpt-4.1-mini"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    inp = (root / args.input).resolve()
    outp = (root / args.output).resolve()

    if not inp.exists():
        print(f"[ERROR] Missing input file: {inp}")
        return 2

    lines = inp.read_text(encoding="utf-8", errors="replace").splitlines()
    issues_out: list[dict] = []
    llm_issues_out: list[dict] = []

    for block in iter_blocks(lines):
        fields = list(iter_block_fields(block))
        de_1 = None
        word = None
        meaning = None
        en_1 = None
        word_inf = None
        for f in fields:
            if f.field_name == "word":
                word = f.field_value.strip()
            if f.field_name == "meaning":
                meaning = f.field_value.strip()
            if f.field_name == "de_1":
                de_1 = f.field_value.strip()
            if f.field_name == "en_1":
                en_1 = f.field_value.strip()
            if f.field_name == "word_inf":
                word_inf = f.field_value.strip()
        if not de_1:
            continue
        issues = qa_de1_issues(de_1)
        for iss in issues:
            issues_out.append(
                {
                    "word": word,
                    "start_line": block.start_line,
                    "end_line": block.end_line,
                    **asdict(iss),
                }
            )

        if args.llm and os.environ.get("OPENAI_API_KEY") and llm_review_entry is not None:
            if word and meaning and en_1 and word_inf:
                async def _run() -> None:
                    res = await llm_review_entry(
                        word=word,
                        meaning=meaning,
                        de_1=de_1,
                        en_1=en_1,
                        word_inf=word_inf,
                        model=args.llm_model,
                    )
                    for issue in res.issues:
                        llm_issues_out.append(
                            {
                                "word": word,
                                "start_line": block.start_line,
                                "end_line": block.end_line,
                                "code": issue.code,
                                "severity": issue.severity,
                                "field": issue.field,
                                "message": issue.message,
                                "evidence": issue.evidence,
                                "suggestion": issue.suggestion,
                            }
                        )

                asyncio.run(_run())

    outp.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "input": str(inp),
        "issues": issues_out,
        "llm_issues": llm_issues_out,
        "issue_count": len(issues_out),
        "llm_issue_count": len(llm_issues_out),
        "env": {
            "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        },
    }
    outp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    if issues_out:
        print(f"[WARN] NW1 QA found {len(issues_out)} issues. Report: {outp}")
        if args.fail_on_issues and any_fail([object() for _ in issues_out]):
            return 1
    else:
        print(f"[OK] NW1 QA: no issues found. Report: {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
