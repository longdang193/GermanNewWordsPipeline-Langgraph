from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from mdproc.validation_core import iter_blocks


@dataclass(frozen=True)
class Nw1Step:
    name: str
    cmd: list[str]
    continue_on_parseable_blocks: bool = False
    allow_nonzero: bool = False


def build_nw1_steps(*, root: Path) -> tuple[Nw1Step, Nw1Step, Nw1Step]:
    scripts = root / "Tools" / "scripts"
    qa_cmd = [sys.executable, str(scripts / "nw1_qa_review.py"), "--root", "."]
    if os.environ.get("GNW_ENABLE_NW1_LLM_QA", "0") == "1":
        qa_cmd.append("--llm")

    return (
        Nw1Step(
            name="nw1_generate",
            cmd=[sys.executable, str(scripts / "process_requirement1.py")],
            continue_on_parseable_blocks=True,
        ),
        Nw1Step(
            name="nw1_validate",
            cmd=[sys.executable, str(scripts / "validate_word_list.py")],
            continue_on_parseable_blocks=True,
        ),
        Nw1Step(
            name="nw1_qa_review",
            cmd=qa_cmd,
            allow_nonzero=True,
        ),
    )


def has_parseable_nw1_blocks(path: Path) -> bool:
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return any(True for _ in iter_blocks(lines))
