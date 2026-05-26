from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


EN_STOPWORD_RE = re.compile(
    r"(?i)\b("
    r"we|you|they|i|he|she|it|need|needs|to|and|or|but|with|without|for|from|"
    r"this|that|these|those|is|are|was|were|be|been|being|have|has|had|do|does|did|"
    r"please|thanks|thank|feed|eat|drink|go|want|like|make|take|give|get|put|"
    r")\b"
)


@dataclass(frozen=True)
class QaIssue:
    code: str
    field: str
    message: str
    evidence: str


def detect_mixed_language_de1(de_1: str) -> list[QaIssue]:
    """Heuristic mixed-language detector for NW1 de_1.

    Goal: catch obvious English tokens in German example sentences.
    """
    hits = list(EN_STOPWORD_RE.finditer(de_1))
    if not hits:
        return []

    # Keep small evidence snippet around first hit.
    h = hits[0]
    start = max(0, h.start() - 20)
    end = min(len(de_1), h.end() + 20)
    evidence = de_1[start:end]
    return [
        QaIssue(
            code="mixed_language_de1",
            field="de_1",
            message="de_1 contains English token(s); should be German-only.",
            evidence=evidence,
        )
    ]


def qa_de1_issues(de_1: str) -> list[QaIssue]:
    issues: list[QaIssue] = []
    issues.extend(detect_mixed_language_de1(de_1))
    return issues


def any_fail(issues: Iterable[QaIssue]) -> bool:
    # For now, treat all QA issues as fail-class.
    return any(True for _ in issues)

