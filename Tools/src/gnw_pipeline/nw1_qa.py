from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Mapping, Sequence

Severity = Literal["hard_fail", "soft_review"]
IssueSource = Literal["deterministic", "llm"]
ResolutionStatus = Literal["clean", "unresolved_part", "omitted"]
WriteDisposition = Literal["written", "duplicate_skipped", "omitted"]
MatchMode = Literal[
    "phrase_contiguous_surface",
    "single_token",
    "noun_surface",
    "verb_explicit_forms",
]

ARTICLE_TOKENS = {
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "einer",
    "einem",
    "einen",
}
CLAUSE_PUNCTUATION = frozenset({",", ";", ":", ".", "!", "?"})
COMMON_PREDICATE_CUES = {
    "ist",
    "sind",
    "war",
    "waren",
    "hat",
    "haben",
    "wird",
    "werden",
    "kann",
    "können",
    "muss",
    "müssen",
    "soll",
    "sollen",
    "will",
    "wollen",
    "darf",
    "dürfen",
    "geht",
    "gehen",
    "kommt",
    "kommen",
    "liegt",
    "liegen",
    "steht",
    "stehen",
    "bleibt",
    "bleiben",
    "gibt",
    "geben",
    "macht",
    "machen",
    "braucht",
    "brauchen",
    "arbeitet",
    "arbeiten",
    "fühlt",
    "fühlen",
}
EN_STOPWORD_RE = re.compile(
    r"(?i)\b("
    r"we|you|they|need|needs|this|that|these|those|please|thanks|thank|"
    r"feed|drink|want|like|make|take|give|without|with"
    r")\b"
)
TOKEN_OR_PUNCT_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)?|[.,;:!?]")
WORD_TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)?")
TAG_SPLIT_RE = re.compile(r"[\s,]+")
ADJECTIVE_ENDINGS = ("em", "en", "er", "es", "e")


@dataclass(frozen=True)
class QaEntry:
    word: str
    meaning: str
    de_1: str
    en_1: str
    word_inf: str
    tags: tuple[str, ...] = ()
    verb_present: str | None = None
    verb_past: str | None = None
    verb_perfect: str | None = None


@dataclass(frozen=True)
class QaIssue:
    code: str
    field: str
    severity: Severity
    message: str
    evidence: str
    source: IssueSource = "deterministic"


@dataclass(frozen=True)
class QaReportRow:
    word: str
    word_inf: str
    start_line: int
    end_line: int
    input_index: int | None = None
    issues: tuple[QaIssue, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "word": self.word,
            "word_inf": self.word_inf,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "input_index": self.input_index,
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True)
class Nw1ResultRow:
    input_index: int
    term: str
    resolution_status: ResolutionStatus
    origin_reason_code: str | None = None
    final_blocker_code: str | None = None
    final_blocker_codes: tuple[str, ...] = field(default_factory=tuple)
    output_section: str | None = None
    write_disposition: WriteDisposition = "written"
    duplicate_of_input_index: int | None = None
    start_line: int | None = None
    end_line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "input_index": self.input_index,
            "term": self.term,
            "resolution_status": self.resolution_status,
            "origin_reason_code": self.origin_reason_code,
            "final_blocker_code": self.final_blocker_code,
            "final_blocker_codes": list(self.final_blocker_codes),
            "output_section": self.output_section,
            "write_disposition": self.write_disposition,
            "duplicate_of_input_index": self.duplicate_of_input_index,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


@dataclass(frozen=True)
class LlmIssueInput:
    code: str
    field: str
    severity: str
    message: str
    evidence: str


def parse_tags(raw_tags: str) -> tuple[str, ...]:
    return tuple(tag for tag in TAG_SPLIT_RE.split(raw_tags.strip()) if tag)


def detect_mixed_language_de1(de_1: str) -> list[QaIssue]:
    """Heuristic mixed-language detector for NW1 de_1."""
    hits = list(EN_STOPWORD_RE.finditer(de_1))
    if not hits:
        return []

    hit = hits[0]
    start = max(0, hit.start() - 20)
    end = min(len(de_1), hit.end() + 20)
    evidence = de_1[start:end]
    return [
        QaIssue(
            code="mixed_language_de1",
            field="de_1",
            severity="hard_fail",
            message="de_1 contains English token(s); should be German-only.",
            evidence=evidence,
        )
    ]


def qa_de1_issues(de_1: str) -> list[QaIssue]:
    """Backward-compatible wrapper for legacy call sites."""
    return detect_mixed_language_de1(de_1)


def qa_entry_from_fields(fields: Mapping[str, str]) -> QaEntry | None:
    de_1 = fields.get("de_1", "").strip()
    if not de_1:
        return None

    return QaEntry(
        word=fields.get("word", "").strip(),
        meaning=fields.get("meaning", "").strip(),
        de_1=de_1,
        en_1=fields.get("en_1", "").strip(),
        word_inf=fields.get("word_inf", fields.get("word", "")).strip(),
        tags=parse_tags(fields.get("Tags", "")),
        verb_present=fields.get("verb_present") or None,
        verb_past=fields.get("verb_past") or None,
        verb_perfect=fields.get("verb_perfect") or None,
    )


def qa_entry_from_block_text(block_text: str) -> QaEntry | None:
    fields: dict[str, str] = {}
    for raw_line in block_text.splitlines():
        line = raw_line.strip()
        if not line or line in {"SSTART", "EEND"} or line.startswith("%"):
            continue
        if ": " not in line:
            continue
        field_name, field_value = line.split(": ", 1)
        fields[field_name] = field_value.strip()
    return qa_entry_from_fields(fields)


def derive_match_mode(entry: QaEntry) -> MatchMode:
    normalized_tags = {tag.casefold() for tag in entry.tags}
    content_tokens = _content_tokens(entry.word_inf or entry.word)

    if _is_verb_entry(entry, normalized_tags):
        return "verb_explicit_forms"
    if len(content_tokens) > 1:
        return "phrase_contiguous_surface"
    if "noun" in normalized_tags:
        return "noun_surface"
    return "single_token"


def qa_entry_issues(entry: QaEntry) -> list[QaIssue]:
    issues: list[QaIssue] = []
    issues.extend(detect_mixed_language_de1(entry.de_1))
    issues.extend(_sentence_shape_issues(entry))
    issues.extend(_target_realization_issues(entry))
    return issues


def build_report_row(
    *,
    entry: QaEntry,
    start_line: int,
    end_line: int,
    deterministic_issues: Sequence[QaIssue],
    llm_issues: Sequence[QaIssue] = (),
) -> QaReportRow:
    return QaReportRow(
        word=entry.word,
        word_inf=entry.word_inf,
        start_line=start_line,
        end_line=end_line,
        issues=tuple(deterministic_issues) + tuple(llm_issues),
    )


def summarize_report(
    *,
    results: Sequence[Nw1ResultRow | Mapping[str, object]],
    issue_rows: Sequence[QaReportRow | Mapping[str, object]],
) -> dict[str, object]:
    resolution_counts = {"clean": 0, "unresolved_part": 0, "omitted": 0}
    duplicate_count = 0
    written_block_count = 0
    for row in results:
        resolution_status = row.resolution_status if isinstance(row, Nw1ResultRow) else str(row.get("resolution_status", ""))
        if resolution_status in resolution_counts:
            resolution_counts[resolution_status] += 1
        write_disposition = row.write_disposition if isinstance(row, Nw1ResultRow) else str(row.get("write_disposition", ""))
        if write_disposition == "duplicate_skipped":
            duplicate_count += 1
        if write_disposition == "written":
            written_block_count += 1

    return {
        "result_count": len(results),
        "issue_row_count": len(issue_rows),
        "issue_count": sum(len(row.issues) if isinstance(row, QaReportRow) else len(row.get("issues", [])) for row in issue_rows),
        "resolution_counts": resolution_counts,
        "written_block_count": written_block_count,
        "duplicate_count": duplicate_count,
        "omitted_count": resolution_counts["omitted"],
    }


def load_report_payload(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "results": [],
            "issue_rows": [],
            "env": {},
            "summary": summarize_report(results=(), issue_rows=()),
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid NW1 report payload: {path}")

    results = payload.get("results")
    issue_rows = payload.get("issue_rows")
    env = payload.get("env")
    summary = payload.get("summary")
    return {
        "results": results if isinstance(results, list) else [],
        "issue_rows": issue_rows if isinstance(issue_rows, list) else [],
        "env": env if isinstance(env, dict) else {},
        "summary": summary if isinstance(summary, dict) else summarize_report(results=(), issue_rows=()),
    }


def write_report_payload(
    path: Path,
    *,
    results: Sequence[Nw1ResultRow | Mapping[str, object]],
    issue_rows: Sequence[QaReportRow | Mapping[str, object]],
    env: Mapping[str, object],
) -> None:
    payload = {
        "results": [row.to_dict() if isinstance(row, Nw1ResultRow) else dict(row) for row in results],
        "issue_rows": [row.to_dict() if isinstance(row, QaReportRow) else dict(row) for row in issue_rows],
        "env": dict(env),
        "summary": summarize_report(results=results, issue_rows=issue_rows),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def normalize_llm_issue(issue: LlmIssueInput) -> QaIssue:
    severity: Severity = "hard_fail" if issue.severity == "fail" else "soft_review"
    return QaIssue(
        code=issue.code,
        field=issue.field,
        severity=severity,
        message=issue.message,
        evidence=issue.evidence,
        source="llm",
    )


def any_fail(issues: Iterable[QaIssue]) -> bool:
    return any(issue.severity == "hard_fail" for issue in issues)


def _sentence_shape_issues(entry: QaEntry) -> list[QaIssue]:
    issues: list[QaIssue] = []
    text = entry.de_1.strip()
    if not text:
        return issues

    last_char = text[-1]
    if last_char in ",;:":
        issues.append(
            QaIssue(
                code="bad_terminal_punctuation",
                field="de_1",
                severity="hard_fail",
                message="de_1 must not end with ',', ';', or ':'.",
                evidence=text,
            )
        )
    elif last_char not in ".!?":
        issues.append(
            QaIssue(
                code="missing_terminal_punctuation",
                field="de_1",
                severity="hard_fail",
                message="de_1 must end with '.', '!', or '?'.",
                evidence=text,
            )
        )

    word_tokens = WORD_TOKEN_RE.findall(text)
    if len(word_tokens) < 3:
        issues.append(
            QaIssue(
                code="too_few_tokens",
                field="de_1",
                severity="hard_fail",
                message="de_1 must contain at least three word tokens.",
                evidence=text,
            )
        )

    first_alpha = _first_alpha_char(text)
    if first_alpha is not None and first_alpha.islower():
        issues.append(
            QaIssue(
                code="sentence_starts_lowercase",
                field="de_1",
                severity="soft_review",
                message="de_1 starts with lowercase alphabetic character.",
                evidence=text,
            )
        )

    if not _has_predicate_cue(entry):
        issues.append(
            QaIssue(
                code="no_predicate_cue",
                field="de_1",
                severity="soft_review",
                message="de_1 has no likely predicate cue.",
                evidence=text,
            )
        )

    return issues


def _target_realization_issues(entry: QaEntry) -> list[QaIssue]:
    match_mode = derive_match_mode(entry)
    if match_mode == "verb_explicit_forms":
        return _verb_realization_issues(entry)

    if _non_verb_target_realized(entry, match_mode):
        return []

    return [
        QaIssue(
            code="target_not_realized",
            field="de_1",
            severity="hard_fail",
            message="de_1 does not realize target lexeme.",
            evidence=entry.de_1,
        )
    ]


def _non_verb_target_realized(entry: QaEntry, match_mode: MatchMode) -> bool:
    target_tokens = _content_tokens(entry.word_inf or entry.word)
    sentence_tokens = _content_tokens(entry.de_1)
    if not target_tokens:
        return True
    if match_mode == "single_token" or match_mode == "noun_surface":
        target = target_tokens[0]
        return any(_token_matches(target, sentence_token) for sentence_token in sentence_tokens)
    return _contiguous_match(target_tokens, sentence_tokens)


def _verb_realization_issues(entry: QaEntry) -> list[QaIssue]:
    explicit_forms = _explicit_verb_forms(entry)
    if any(_verb_form_matches_sentence(form, entry.de_1) for form in explicit_forms):
        return []
    if _looks_like_unstored_verb_realization(entry):
        return [
            QaIssue(
                code="verb_realization_inconclusive",
                field="de_1",
                severity="soft_review",
                message="de_1 may realize target verb using unstored conjugation.",
                evidence=entry.de_1,
            )
        ]
    return [
        QaIssue(
            code="target_not_realized",
            field="de_1",
            severity="hard_fail",
            message="de_1 does not realize target verb through explicit stored forms.",
            evidence=entry.de_1,
        )
    ]


def _verb_form_matches_sentence(form: str, sentence: str) -> bool:
    normalized_form_tokens = _content_tokens(form, drop_articles=False)
    if not normalized_form_tokens:
        return False
    clause_tokens = _sentence_clauses(sentence)
    if len(normalized_form_tokens) == 1:
        return any(normalized_form_tokens[0] in clause for clause in clause_tokens)
    if len(normalized_form_tokens) == 2:
        first_token, second_token = normalized_form_tokens
        for clause in clause_tokens:
            if first_token not in clause or second_token not in clause:
                continue
            first_index = clause.index(first_token)
            second_index = clause.index(second_token)
            if first_index < second_index:
                return True
        return False
    for clause in clause_tokens:
        if _ordered_subsequence_match(normalized_form_tokens, clause):
            return True
    return False


def _looks_like_unstored_verb_realization(entry: QaEntry) -> bool:
    sentence_tokens = _content_tokens(entry.de_1, drop_articles=False)
    if not sentence_tokens:
        return False

    particle = _verb_particle(entry.word_inf)
    if not particle or particle not in sentence_tokens:
        return False

    explicit_forms = _explicit_verb_forms(entry)
    finite_tokens = [_content_tokens(form, drop_articles=False)[0] for form in explicit_forms if _content_tokens(form, drop_articles=False)]
    if not finite_tokens:
        return False

    stems = {_verb_stem(token) for token in finite_tokens}
    for token in sentence_tokens:
        if any(_verb_stem(token) == stem for stem in stems if stem):
            if token not in finite_tokens:
                return True
    return False


def _has_predicate_cue(entry: QaEntry) -> bool:
    sentence_tokens = _content_tokens(entry.de_1, drop_articles=False)
    if not sentence_tokens:
        return False
    lowered_tokens = set(sentence_tokens)
    if lowered_tokens & COMMON_PREDICATE_CUES:
        return True
    normalized_tags = {tag.casefold() for tag in entry.tags}
    if _is_verb_entry(entry, normalized_tags):
        for form in _explicit_verb_forms(entry):
            form_tokens = _content_tokens(form, drop_articles=False)
            if form_tokens and _verb_form_matches_sentence(form, entry.de_1):
                return True
    return False


def _explicit_verb_forms(entry: QaEntry) -> tuple[str, ...]:
    values = [entry.word_inf, entry.verb_present, entry.verb_past, entry.verb_perfect]
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = value.strip()
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized)
    return tuple(out)


def _is_verb_entry(entry: QaEntry, normalized_tags: set[str]) -> bool:
    return "verb" in normalized_tags or any(
        value for value in (entry.verb_present, entry.verb_past, entry.verb_perfect)
    )


def _content_tokens(text: str, *, drop_articles: bool = True) -> list[str]:
    out: list[str] = []
    for match in WORD_TOKEN_RE.findall(text):
        normalized = match.casefold()
        if drop_articles and normalized in ARTICLE_TOKENS:
            continue
        out.append(normalized)
    return out


def _sentence_clauses(text: str) -> list[list[str]]:
    clauses: list[list[str]] = [[]]
    for token in TOKEN_OR_PUNCT_RE.findall(text):
        if token in CLAUSE_PUNCTUATION:
            clauses.append([])
            continue
        clauses[-1].append(token.casefold())
    return [clause for clause in clauses if clause]


def _ordered_subsequence_match(target_tokens: Sequence[str], sentence_tokens: Sequence[str]) -> bool:
    target_index = 0
    for sentence_token in sentence_tokens:
        if target_index >= len(target_tokens):
            break
        if _token_matches(target_tokens[target_index], sentence_token):
            target_index += 1
    return target_index == len(target_tokens)


def _contiguous_match(target_tokens: Sequence[str], sentence_tokens: Sequence[str]) -> bool:
    if not target_tokens:
        return True
    width = len(target_tokens)
    if width > len(sentence_tokens):
        return False
    for start in range(len(sentence_tokens) - width + 1):
        window = sentence_tokens[start : start + width]
        if all(_token_matches(target_token, sentence_token) for target_token, sentence_token in zip(target_tokens, window)):
            return True
    return False


def _token_matches(target_token: str, sentence_token: str) -> bool:
    if target_token == sentence_token:
        return True
    return _fold_modifier_token(target_token) == _fold_modifier_token(sentence_token)


def _fold_modifier_token(token: str) -> str:
    for ending in ADJECTIVE_ENDINGS:
        if token.endswith(ending) and len(token) > len(ending) + 2:
            return token[: -len(ending)]
    return token


def _first_alpha_char(text: str) -> str | None:
    for char in text:
        if char.isalpha():
            return char
    return None


def _verb_particle(word_inf: str) -> str | None:
    particles = (
        "ab",
        "an",
        "auf",
        "aus",
        "bei",
        "ein",
        "fest",
        "fort",
        "her",
        "hin",
        "los",
        "mit",
        "nach",
        "vor",
        "weg",
        "wieder",
        "zu",
        "zurück",
        "zusammen",
    )
    lowered = word_inf.casefold()
    for particle in particles:
        if lowered.startswith(particle) and len(lowered) > len(particle) + 2:
            return particle
    return None


def _verb_stem(token: str) -> str:
    lowered = token.casefold()
    for ending in ("est", "st", "en", "et", "te", "t"):
        if lowered.endswith(ending) and len(lowered) > len(ending) + 2:
            return lowered[: -len(ending)]
    return lowered
