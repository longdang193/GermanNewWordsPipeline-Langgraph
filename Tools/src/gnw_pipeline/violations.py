from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RequirementId(str, Enum):
    NW1 = "NW1"
    NW2 = "NW2"
    NW3 = "NW3"
    NW4 = "NW4"


class RuleId(str, Enum):
    NW1_ANTI_PLACEHOLDER = "NW1_ANTI_PLACEHOLDER"
    NW1_WORD_HYGIENE = "NW1_WORD_HYGIENE"
    NW1_EXAMPLE_LANGUAGE = "NW1_EXAMPLE_LANGUAGE"
    NW4_SEEALSO_CANONICAL = "NW4_SEEALSO_CANONICAL"
    NW4_NOUN_FORMS_CONSISTENCY = "NW4_NOUN_FORMS_CONSISTENCY"


Severity = Literal["warn", "fail"]
FieldName = Literal[
    "word",
    "meaning",
    "de_1",
    "en_1",
    "word_inf",
    "tags",
    "see_also",
    "noun_forms",
]


class Violation(BaseModel):
    requirement: RequirementId
    rule_id: RuleId
    severity: Severity
    field: FieldName
    message: str
    evidence: str | None = None
    fix_hint: str | None = None
    meta: dict[str, str] = Field(default_factory=dict)

