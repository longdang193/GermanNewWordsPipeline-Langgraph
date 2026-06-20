from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


BLOCK_START = "SSTART"
BLOCK_END = "EEND"
FIELD_HEADER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*:")
TAGS_SPLIT_RE = re.compile(r"[\s,]+")
WORD_HAS_PARENS_RE = re.compile(r"[()]")
WORD_LEADING_ARTICLE_RE = re.compile(r"(?i)^(?:der|die|das)\s+")
PLACEHOLDER_VALUE_RE = re.compile(
    r"(?i)("
    r"\[[^\]]*(?:simple german meaning|english meaning|german meaning|example sentence|translation|word or phrase|lemma|part of speech|infinitive|präteritum|perfekt|3rd person singular|form|endings)[^\]]*\]"
    r"|"
    r"\([^\)]*(?:example sentence|translation|word or phrase|lemma|part of speech|infinitive|präteritum|perfekt|3rd person singular|form|endings)[^\)]*\)"
    r")"
)
CANONICAL_SEE_ALSO_RE = re.compile(
    r"^(?:(?:der|die|das|\([^)]+\))\s+)?\[[^|\]]+\|nid\d+\]\s*=\s*.+$"
)
ENTRY_PARSE_RE = re.compile(
    r"^(?:(?P<article>der|die|das|\([^)]+\))\s+)?\[(?P<term>[^|\]]+)\|nid\d+\]\s*=\s*.+$"
)
REQUIRED_CORE_FIELDS = ("word", "meaning", "de_1", "en_1", "Tags")
MEANING_SPLIT_RE = re.compile(r"^(?P<lhs>.+?)\s*=\s*(?P<gloss_de>.+?)\s*/\s*(?P<gloss_en>.+?)$")


@dataclass(frozen=True)
class ValidationPathResult:
    path: Path | None
    messages: list[str]
    drift_detected: bool


@dataclass(frozen=True)
class Block:
    start_line: int
    end_line: int
    lines: list[str]

    @property
    def body_lines(self) -> list[str]:
        return self.lines[1:-1]


@dataclass(frozen=True)
class FieldLine:
    line_number: int
    field_name: str
    field_value: str


def resolve_with_legacy(preferred: Path, legacy: Path, label: str = "validation target") -> ValidationPathResult:
    """Resolve preferred path with legacy fallback and drift warnings."""
    messages: list[str] = []
    drift_detected = False

    if preferred.exists() and legacy.exists():
        drift_detected = True
        messages.append(
            f"[WARN] Path drift detected for {label}: both preferred and legacy files exist."
        )
        messages.append(f"   Preferred: {preferred}")
        messages.append(f"   Legacy:    {legacy}")
        return ValidationPathResult(preferred, messages, drift_detected)

    if preferred.exists():
        return ValidationPathResult(preferred, messages, drift_detected)

    if legacy.exists():
        drift_detected = True
        messages.append(
            f"[WARN] Path drift detected for {label}: using legacy path."
        )
        messages.append(f"   Expected: {preferred}")
        messages.append(f"   Legacy:   {legacy}")
        return ValidationPathResult(legacy, messages, drift_detected)

    messages.append(f"[ERROR] Missing {label} file: {preferred}")
    messages.append(f"   Legacy path also missing: {legacy}")
    return ValidationPathResult(None, messages, drift_detected)


def analyze_block_structure(lines: list[str], label: str = "validation target") -> tuple[int, list[str]]:
    """Return strict block count and structural issues."""
    content = "\n".join(lines)
    sstart_count = len(re.findall(r"^\s*SSTART\s*$", content, re.MULTILINE))
    eend_count = len(re.findall(r"^\s*EEND\s*$", content, re.MULTILINE))
    legacy_start_count = len(re.findall(r"^\s*START\s*$", content, re.MULTILINE))
    legacy_end_count = len(re.findall(r"^\s*END\s*$", content, re.MULTILINE))

    issues: list[str] = []
    if legacy_start_count or legacy_end_count:
        issues.append(
            "Invalid block indicators found: "
            f"START={legacy_start_count}, END={legacy_end_count}. "
            "Expected strict SSTART...EEND markers."
        )

    if sstart_count != eend_count:
        issues.append(
            f"Mismatched strict block indicators: SSTART={sstart_count}, EEND={eend_count}."
        )

    if sstart_count == 0:
        issues.append(f"No SSTART...EEND blocks found in {label}.")

    return sstart_count, issues


def iter_blocks(lines: list[str]) -> Iterator[Block]:
    """Yield each strict SSTART...EEND block with 1-based line numbers."""
    index = 0
    while index < len(lines):
        if lines[index].strip() != BLOCK_START:
            index += 1
            continue

        start = index
        end = index + 1
        while end < len(lines) and lines[end].strip() != BLOCK_END:
            end += 1

        if end >= len(lines):
            break

        yield Block(start + 1, end + 1, lines[start: end + 1])
        index = end + 1


def iter_block_field_lines(lines: list[str]) -> Iterator[FieldLine]:
    """Yield parsed field lines that appear inside strict blocks."""
    for block in iter_blocks(lines):
        for offset, raw in enumerate(block.body_lines, 1):
            stripped = raw.strip()
            if not FIELD_HEADER_RE.match(stripped):
                continue

            field_name, field_value = stripped.split(":", 1)
            yield FieldLine(
                line_number=block.start_line + offset,
                field_name=field_name.strip(),
                field_value=field_value.strip(),
            )


def extract_block_fields(block: Block) -> tuple[dict[str, str], dict[str, int]]:
    """Return first-occurrence field values and their line numbers for a block."""
    values: dict[str, str] = {}
    line_numbers: dict[str, int] = {}

    for field in iter_block_fields(block):
        if field.field_name not in values:
            values[field.field_name] = field.field_value
            line_numbers[field.field_name] = field.line_number

    return values, line_numbers


def iter_block_fields(block: Block) -> Iterator[FieldLine]:
    """Yield parsed field lines for a single block."""
    for offset, raw in enumerate(block.body_lines, 1):
        stripped = raw.strip()
        if not FIELD_HEADER_RE.match(stripped):
            continue

        field_name, field_value = stripped.split(":", 1)
        yield FieldLine(
            line_number=block.start_line + offset,
            field_name=field_name.strip(),
            field_value=field_value.strip(),
        )


def extract_word_and_line(block: Block) -> tuple[str, int]:
    """Extract block word value and source line number for reporting."""
    for field in iter_block_fields(block):
        if field.field_name == "word":
            return field.field_value or "<empty>", field.line_number
    return "<unknown>", block.start_line


def iter_see_also_entries(lines: Iterable[str]) -> list[str]:
    """Return normalized see_also entry lines only, excluding field headers."""
    entries: list[str] = []
    in_see_also = False

    for raw in lines:
        stripped = raw.strip()
        if stripped == "see_also:":
            in_see_also = True
            continue

        if not in_see_also:
            continue

        if stripped and FIELD_HEADER_RE.match(stripped):
            in_see_also = False
            continue

        if stripped:
            entries.append(stripped)

    return entries


def validate_placeholder_values(lines: list[str]) -> list[str]:
    """Reject unreplaced template placeholders inside block field values."""
    issues: list[str] = []

    for field in iter_block_field_lines(lines):
        if not field.field_value or field.field_name == "see_also":
            continue

        if PLACEHOLDER_VALUE_RE.search(field.field_value):
            issues.append(
                f"Line {field.line_number}: Placeholder text detected in field '{field.field_name}' -> '{field.field_value}'"
            )
            continue

        if re.fullmatch(r"\[[^\]]+\]", field.field_value) and "|nid" not in field.field_value:
            issues.append(
                f"Line {field.line_number}: Unresolved bracket placeholder in field '{field.field_name}' -> '{field.field_value}'"
            )

    return issues


def validate_word_field_rules(lines: list[str]) -> list[str]:
    """Validate word field hygiene across all blocks."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        values, line_numbers = extract_block_fields(block)
        word = values.get("word", "")
        if not word:
            continue

        tags = split_tags(values.get("Tags", ""))
        word_line = line_numbers.get("word", block.start_line)

        if WORD_HAS_PARENS_RE.search(word):
            issues.append(
                f"Line {word_line}: word field must not include parenthetical meaning/gloss -> '{word}'"
            )

        if "noun" in tags and WORD_LEADING_ARTICLE_RE.match(word):
            issues.append(
                f"Line {word_line}: noun word field must not start with der/die/das -> '{word}'"
            )

    return issues


def _normalize_meaning_fragment(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().casefold())
    normalized = normalized.replace("…", "...")
    return normalized


def validate_meaning_field_rules(lines: list[str]) -> list[str]:
    """Validate NW1 meaning contract, with stricter noun rules."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        values, line_numbers = extract_block_fields(block)
        meaning = values.get("meaning", "")
        if not meaning:
            continue

        meaning_line = line_numbers.get("meaning", block.start_line)
        word = values.get("word", "").strip()
        tags = split_tags(values.get("Tags", ""))
        noun_gender = values.get("noun_gender", "").strip()
        word_inf = values.get("word_inf", "").strip()

        match = MEANING_SPLIT_RE.match(meaning)
        if not match:
            issues.append(
                f"Line {meaning_line}: meaning field must match '<term> = <German gloss> / <English gloss>' -> '{meaning}'"
            )
            continue

        lhs = match.group("lhs").strip()
        gloss_de = match.group("gloss_de").strip()
        gloss_en = match.group("gloss_en").strip()

        if not gloss_de or not gloss_en:
            issues.append(
                f"Line {meaning_line}: meaning field must contain non-empty German and English glosses -> '{meaning}'"
            )
            continue

        normalized_word = _normalize_meaning_fragment(word)
        normalized_lhs = _normalize_meaning_fragment(lhs)
        normalized_gloss_de = _normalize_meaning_fragment(gloss_de)

        if "noun" in tags and noun_gender in {"der", "die", "das"}:
            expected_lhs_text = word_inf or f"{noun_gender} {word}"
            expected_lhs = _normalize_meaning_fragment(expected_lhs_text)
            if normalized_lhs != expected_lhs:
                issues.append(
                    f"Line {meaning_line}: noun meaning must start with article-bearing lemma '{expected_lhs_text}' -> '{meaning}'"
                )

            circular_targets = {
                normalized_word,
                expected_lhs,
            }
            if normalized_gloss_de in circular_targets:
                issues.append(
                    f"Line {meaning_line}: noun meaning gloss must not repeat the noun itself -> '{meaning}'"
                )

    return issues


def validate_required_core_fields(lines: list[str]) -> list[str]:
    """Require non-empty core fields on every vocabulary block."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        values, line_numbers = extract_block_fields(block)
        first_word, first_word_line = extract_word_and_line(block)

        for field_name in REQUIRED_CORE_FIELDS:
            if field_name not in values:
                issues.append(
                    f"Line {first_word_line}: missing required field '{field_name}' in block '{first_word}'"
                )
                continue

            if not values[field_name]:
                issues.append(
                    f"Line {line_numbers[field_name]}: required field '{field_name}' is empty in block '{first_word}'"
                )

    return issues


def validate_unique_fields_per_block(lines: list[str]) -> list[str]:
    """Reject repeated field names and repeated %VOCAB headers within a block."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        seen_fields: dict[str, int] = {}
        vocab_header_lines: list[int] = []
        block_word, block_word_line = extract_word_and_line(block)

        for offset, raw in enumerate(block.body_lines, 1):
            stripped = raw.strip()
            line_number = block.start_line + offset

            if stripped == "%VOCAB (German) ver 3":
                vocab_header_lines.append(line_number)
                continue

            if ":" not in stripped:
                continue

            field_name = stripped.split(":", 1)[0].strip()
            if field_name in seen_fields:
                issues.append(
                    f"Line {line_number}: duplicate field '{field_name}' in block '{block_word}' (first seen at line {seen_fields[field_name]})"
                )
            else:
                seen_fields[field_name] = line_number

        if len(vocab_header_lines) > 1:
            issues.append(
                f"Line {vocab_header_lines[1]}: duplicate %VOCAB header in block '{block_word}' (first seen at line {vocab_header_lines[0]})"
            )

    return issues


def validate_tags_last(lines: list[str]) -> list[str]:
    """Require Tags to be the final field in each block before EEND."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        tag_line_number: int | None = None
        tag_seen = False

        for field in iter_block_fields(block):
            if field.field_name == "Tags":
                tag_seen = True
                tag_line_number = field.line_number
                continue

            if tag_seen:
                issues.append(
                    f"Line {tag_line_number}: Tags field must be the last field before EEND in block '{extract_word_and_line(block)[0]}'"
                )
                break

    return issues


def validate_no_blank_lines_between_fields(lines: list[str]) -> list[str]:
    """Reject blank separator lines inside blocks."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        for offset, raw in enumerate(block.body_lines, 1):
            if raw.strip():
                continue

            issues.append(
                f"Line {block.start_line + offset}: blank lines are not allowed between fields in block '{extract_word_and_line(block)[0]}'"
            )

    return issues


def validate_single_word_requires_see_also(lines: list[str]) -> list[str]:
    """Require see_also for non-phrase lexical entries."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        word, word_line = extract_word_and_line(block)
        values, _line_numbers = extract_block_fields(block)
        tags = split_tags(values.get("Tags", ""))
        see_also_entries = extract_block_see_also_entries(block)

        if "phrase" in tags:
            continue

        if not see_also_entries:
            issues.append(
                f"Line {word_line}: non-phrase block '{word}' must contain a non-empty see_also field"
            )

    return issues


def extract_block_see_also_entries(block: Block) -> list[str]:
    """Return see_also entries from a single block."""
    return iter_see_also_entries(block.body_lines)


def find_noncanonical_reference_entries(entries: list[str]) -> list[str]:
    """Return see_also lines that contain nid but do not follow canonical syntax."""
    return [entry for entry in entries if "|nid" in entry and not CANONICAL_SEE_ALSO_RE.match(entry)]


def split_tags(tag_value: str) -> set[str]:
    """Normalize Tags field into a comparable lowercase token set."""
    return {token for token in TAGS_SPLIT_RE.split(tag_value.lower()) if token}


def looks_like_noun_candidate(term: str) -> bool:
    """Heuristic for noun-like terms that should carry articles in see_also."""
    token = term.strip()
    if not token:
        return False

    if token.lower() == "weihnachten":
        return False

    if token.upper() == token and len(token) > 1:
        return False

    parts = token.split()
    if len(parts) == 1:
        first_char = token[0]
        return first_char.isalpha() and first_char.upper() == first_char

    if len(parts) > 3:
        return False

    connector_words = {
        "am",
        "an",
        "auf",
        "aus",
        "bei",
        "da",
        "de",
        "dem",
        "den",
        "der",
        "des",
        "die",
        "dos",
        "du",
        "für",
        "im",
        "in",
        "mit",
        "nach",
        "oder",
        "ohne",
        "und",
        "vom",
        "von",
        "zu",
        "zum",
        "zur",
    }

    for part in parts[1:]:
        if not part:
            return False
        if part.lower() in connector_words:
            continue
        if not part[0].isupper():
            return False

    return parts[0][0].isupper()
