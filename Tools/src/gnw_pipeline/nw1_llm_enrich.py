from __future__ import annotations

import asyncio
import os
from typing import Literal

from pydantic import BaseModel, Field
from pathlib import Path

from gnw_pipeline.env import load_dotenv_if_present
from gnw_pipeline.llm_runtime import build_openai_compatible_model, resolve_structured_output
from gnw_pipeline.prompts import load_prompt


class EnrichIssue(BaseModel):
    message: str
    evidence: str = Field(default="")


class EnrichedOverride(BaseModel):
    tags: Literal["noun", "verb", "adj", "adv", "phrase", "sentence", "other"]
    meaning: str
    de_1: str
    en_1: str
    word_inf: str

    noun_gender: Literal["der", "die", "das"] | None = None
    noun_genetiv: str | None = None
    noun_plural: str | None = None
    noun_forms: str | None = None

    verb_present: str | None = None
    verb_past: str | None = None
    verb_perfect: str | None = None


def _enrich_system(root: Path) -> str:
    return load_prompt("nw1_enrich_system", root=root)


def _enrich_instructions(root: Path) -> str:
    return load_prompt("nw1_enrich_instructions", root=root)


def _get_model_and_agent(model_name: str):
    from pydantic_ai import Agent

    root = Path(os.getcwd()).resolve()
    model = build_openai_compatible_model(model_name, root=root)
    output_type = resolve_structured_output(model_name, EnrichedOverride, root=root)
    agent = Agent(model, system_prompt=_enrich_system(root), output_type=output_type)
    return agent


async def llm_enrich_term_async(*, term: str, meaning_hint: str | None = None) -> EnrichedOverride:
    root = Path(os.getcwd()).resolve()
    load_dotenv_if_present(root)

    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    agent = _get_model_and_agent(model_name)

    prompt = _enrich_instructions(root).strip() + "\n\n" + f"TERM: {term.strip()}\n"
    if meaning_hint:
        prompt += f"MEANING_HINT: {meaning_hint.strip()}\n"

    res = await agent.run(prompt)
    out = res.output
    out.meaning = out.meaning.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    out.meaning = out.meaning.replace("  ", " ").strip()
    return out


def llm_enrich_term(*, term: str, meaning_hint: str | None = None) -> EnrichedOverride:
    return asyncio.run(llm_enrich_term_async(term=term, meaning_hint=meaning_hint))
