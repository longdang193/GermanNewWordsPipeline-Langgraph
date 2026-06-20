from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from gnw_pipeline.llm_runtime import build_openai_compatible_model, resolve_structured_output
from gnw_pipeline.prompts import load_prompt


class ReviewIssue(BaseModel):
    code: Literal[
        "mixed_language_de1",
        "unnatural_de1",
        "en1_not_translation",
        "meaning_not_definition",
        "placeholder_like",
        "other",
    ]
    severity: Literal["warn", "fail"]
    field: Literal["word", "meaning", "de_1", "en_1", "word_inf", "tags"]
    message: str
    evidence: str = Field(default="")
    suggestion: str | None = None


class ReviewResult(BaseModel):
    ok: bool
    issues: list[ReviewIssue] = Field(default_factory=list)


@dataclass(frozen=True)
class LlmQaConfig:
    model: str


QA_SYSTEM = (
    "You are a strict QA reviewer for German vocabulary flashcard entries. "
    "Return only JSON matching schema. No extra text."
)


QA_INSTRUCTIONS = """
Review entry quality for language-learning constraints:
- de_1: must be natural spoken German (B1–B2), German-only (allow proper nouns), no English helper words.
- en_1: must be translation of de_1 (not definition).
- meaning: must be real definition/meaning, not meta/template filler.
- Avoid placeholder/template-like sentences.

If any fail: ok=false and include issues with exact evidence substring from offending field.
If clean: ok=true and issues=[].
"""


async def llm_review_entry(
    *,
    word: str,
    meaning: str,
    de_1: str,
    en_1: str,
    word_inf: str,
    model: str,
) -> ReviewResult:
    # Lazy import to keep base install light.
    from pydantic_ai import Agent  # type: ignore[import-not-found]
    from pathlib import Path

    repo_root = Path.cwd()
    system_prompt = load_prompt("nw1_qa_system", root=repo_root)
    instructions = load_prompt("nw1_qa_instructions", root=repo_root)
    llm_model = build_openai_compatible_model(model, root=repo_root)
    output_type = resolve_structured_output(model, ReviewResult, root=repo_root)

    agent = Agent(
        llm_model,
        system_prompt=system_prompt,
        output_type=output_type,
    )

    prompt = (
        instructions.strip()
        + "\n\n"
        + "ENTRY:\n"
        + f"word: {word}\n"
        + f"meaning: {meaning}\n"
        + f"de_1: {de_1}\n"
        + f"en_1: {en_1}\n"
        + f"word_inf: {word_inf}\n"
    )

    res = await agent.run(prompt)
    return res.output
