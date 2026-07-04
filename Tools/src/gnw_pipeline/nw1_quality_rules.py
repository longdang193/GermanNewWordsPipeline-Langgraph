from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from mdproc.validation_core import iter_block_field_lines


GENERIC_MEANING_MARKERS = (
    "Ausdruck im Themenkontext",
    "context-specific expression",
    "In diesem Kontext ist",
    "is particularly important",
    "nuetzlicher Ausdruck fuer Kommunikation",
    "useful expression for communication",
    "zentrales Nomen im Lernkontext",
    "key noun in this learning context",
    "Handlung oder Vorgang im Alltag",
    "action or process in everyday life",
    "Ausdruck mit erklaerendem Zusatz",
    "konkrete Bedeutung im aktuellen Themenfeld",
    "konkrete Formulierung im Themenfeld",
    "Nomen im Themenkontext",
    "Verb fuer Handlung im Kontext",
    "Bedeutung als Verb im aktuellen Themenfeld",
    "contextual noun meaning",
    "contextual meaning",
    "verb meaning in this topic",
    "This full phrase is used directly in the example.",
)

GENERIC_LINE_PATTERNS = (
    re.compile(r"^meaning:\s*.+?=\s*nuetzlicher Ausdruck fuer Kommunikation\s*/\s*useful expression for communication\s*$", re.IGNORECASE),
    re.compile(r"^meaning:\s*.+?=\s*zentrales Nomen im Lernkontext\s*/\s*key noun in this learning context\s*$", re.IGNORECASE),
    re.compile(r"^meaning:\s*.+?=\s*Handlung oder Vorgang im Alltag\s*/\s*action or process in everyday life\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*Wir verwenden .+ oft in alltaeglichen Situationen\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*We often use .+ in everyday situations\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*Der Begriff .+ ist in diesem Thema besonders wichtig\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*The term .+ is especially important in this topic\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*Im Text kommt .+ mehrmals vor\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*The word .+ appears several times in the text\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*Im Unterricht besprechen wir .+\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*In class, we discuss .+\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*Wir setzen das Wort .+ in einem klaren Satz ein\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*We use the word .+ in a clear sentence\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*.+ taucht in diesem Abschnitt mehrfach auf\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*This term appears several times in this section\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*This sentence pattern is used to describe sequence and timing\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*Bei diesem Thema spielt .+ eine wichtige Rolle\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*.+ spielt bei dieser Aufgabe eine wichtige Rolle\.?\s*$", re.IGNORECASE),
    re.compile(r"^de_1:\s*Im Arbeitsalltag brauchen wir .+ regelm[aä]ssig\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*.+ plays an important role in this (?:topic|task)\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*We regularly need .+ in everyday work\.?\s*$", re.IGNORECASE),
    re.compile(r"^en_1:\s*This full phrase is used directly in the example\.?\s*$", re.IGNORECASE),
)


@dataclass(frozen=True)
class Nw1GenericContentIssue:
    code: str
    field: str
    line_number: int
    message: str
    evidence: str


def find_generic_content_issues(lines: Sequence[str]) -> list[Nw1GenericContentIssue]:
    issues: list[Nw1GenericContentIssue] = []
    for field in iter_block_field_lines(list(lines)):
        line_num = field.line_number
        field_name = field.field_name
        field_value = field.field_value
        if not field_value:
            continue

        if field_name == "meaning":
            for marker in GENERIC_MEANING_MARKERS:
                if marker in field_value:
                    issues.append(
                        Nw1GenericContentIssue(
                            code="generic_content",
                            field=field_name,
                            line_number=line_num,
                            message=f"Generic meaning detected in '{field_name}'",
                            evidence=field_value,
                        )
                    )
                    break

        full_line = f"{field_name}: {field_value}"
        for pattern in GENERIC_LINE_PATTERNS:
            if pattern.match(full_line):
                issues.append(
                    Nw1GenericContentIssue(
                        code="generic_content",
                        field=field_name,
                        line_number=line_num,
                        message=f"Generic example sentence in '{field_name}'",
                        evidence=field_value,
                    )
                )
                break

    return issues
