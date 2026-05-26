from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptSpec:
    rel_path: str
    required_placeholders: tuple[str, ...] = ()


PROMPTS: dict[str, PromptSpec] = {
    "nw1_enrich_system": PromptSpec("Prompt/nw1_enrich_system.txt"),
    "nw1_enrich_instructions": PromptSpec("Prompt/nw1_enrich_instructions.md"),
    "nw1_qa_system": PromptSpec("Prompt/nw1_qa_system.txt"),
    "nw1_qa_instructions": PromptSpec("Prompt/nw1_qa_instructions.md"),
    "nw3_notebooklm_query": PromptSpec(
        "Prompt/nw3_notebooklm_query.md",
        required_placeholders=("{word_list}",),
    ),
}


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "Tools" / "scripts" / "run_full_pipeline.py").exists() and (cur / "Prompt").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def load_prompt(name: str, *, root: Path | None = None) -> str:
    if name not in PROMPTS:
        raise KeyError(f"Unknown prompt name: {name}")

    repo_root = _find_repo_root(root or Path.cwd())
    spec = PROMPTS[name]
    path = repo_root / spec.rel_path
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}")

    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        raise ValueError(f"Empty prompt file: {path}")

    for ph in spec.required_placeholders:
        if ph not in text:
            raise ValueError(f"Prompt missing required placeholder {ph}: {path}")

    return text


def render_prompt(template: str, *, values: dict[str, str]) -> str:
    rendered = template
    for k, v in values.items():
        rendered = rendered.replace("{" + k + "}", v)

    # Fail if unresolved placeholders remain.
    leftovers = set(re.findall(r"{[a-zA-Z_][a-zA-Z0-9_]*}", rendered))
    if leftovers:
        raise ValueError(f"Unresolved prompt placeholders: {sorted(leftovers)}")
    return rendered

