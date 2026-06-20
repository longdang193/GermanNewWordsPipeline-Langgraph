#!/usr/bin/env python3
"""
Validate that Outputs/01_words.md contains all words from Requirement NW1's Word List.

This script:
1. Extracts and deduplicates the Word List from Requirement NW1
2. Counts the unique words in the list
3. Validates strict SSTART...EEND block indicators in Outputs/01_words.md
4. Compares the counts to ensure completeness
5. Reports path drift when legacy locations are used
6. Rejects unreplaced template placeholders in vocabulary fields
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mdproc.validation_core import (
    analyze_block_structure,
    iter_blocks,
    iter_block_field_lines,
    validate_meaning_field_rules,
    validate_no_blank_lines_between_fields,
    resolve_with_legacy,
    validate_placeholder_values,
    validate_required_core_fields,
    validate_tags_last,
    validate_unique_fields_per_block,
    validate_word_field_rules,
)

GENERIC_MEANING_MARKERS = (
    "konkrete Bedeutung im aktuellen Themenfeld",
    "konkrete Formulierung im Themenfeld",
    "Nomen im Themenkontext",
    "Verb fuer Handlung im Kontext",
    "Bedeutung als Verb im aktuellen Themenfeld",
    "contextual noun meaning",
    "contextual meaning",
    "verb meaning in this topic",
)

GENERIC_LINE_PATTERNS = (
    re.compile(
        r"^de_1:\s*Im Text kommt .+ mehrmals vor\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^en_1:\s*The word .+ appears several times in the text\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^de_1:\s*Im Unterricht besprechen wir .+\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^en_1:\s*In class, we discuss .+\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^de_1:\s*Wir setzen das Wort .+ in einem klaren Satz ein\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^en_1:\s*We use the word .+ in a clear sentence\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^de_1:\s*.+ taucht in diesem Abschnitt mehrfach auf\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^en_1:\s*This term appears several times in this section\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^en_1:\s*This sentence pattern is used to describe sequence and timing\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^de_1:\s*Bei diesem Thema spielt .+ eine wichtige Rolle\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^de_1:\s*.+ spielt bei dieser Aufgabe eine wichtige Rolle\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^de_1:\s*Im Arbeitsalltag brauchen wir .+ regelm[aä]ssig\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^en_1:\s*.+ plays an important role in this (?:topic|task)\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^en_1:\s*We regularly need .+ in everyday work\.?\s*$", re.IGNORECASE),
)

UNRESOLVED_JSON_RE = re.compile(r"<!--\s*UNRESOLVED_JSON\s*:\s*(.*?)\s*-->")
UNRESOLVED_RE = re.compile(r"<!--\s*UNRESOLVED\s*:\s*(.*?)\s*-->")


def extract_unresolved_words(lines: list[str]) -> list[str]:
    """Extract unresolved words from structured or legacy unresolved comments."""
    content = "\n".join(lines)

    m_json = UNRESOLVED_JSON_RE.search(content)
    if m_json:
        raw_json = m_json.group(1).strip()
        if raw_json:
            try:
                payload = json.loads(raw_json)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, list):
                json_words = [item.strip() for item in payload if isinstance(item, str) and item.strip()]
                json_seen: set[str] = set()
                json_uniq: list[str] = []
                for w in json_words:
                    k = w.casefold()
                    if k in json_seen:
                        continue
                    json_seen.add(k)
                    json_uniq.append(w)
                return json_uniq

    m = UNRESOLVED_RE.search(content)
    if not m:
        return []
    raw = m.group(1).strip()
    if not raw:
        return []
    out: list[str] = []
    for part in raw.split(","):
        w = part.strip()
        if w:
            out.append(w)
    seen: set[str] = set()
    uniq: list[str] = []
    for w in out:
        k = w.casefold()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(w)
    return uniq

def extract_word_list_source(requirement_path: Path, fallback_word_list_path: Path) -> tuple[str, str]:
    """Return raw word-list text and a human-readable source description."""
    content = requirement_path.read_text(encoding="utf-8")

    # Prefer inline Word List section if present (legacy format).
    match = re.search(r"## Word List\s*\n(.*?)(?:\n## |\Z)",
                      content, re.DOTALL)
    if match:
        return match.group(1), f"{requirement_path.name} (## Word List section)"

    # New workflow uses Inputs/Word List (DE).md.
    if fallback_word_list_path.exists():
        return fallback_word_list_path.read_text(encoding="utf-8"), str(fallback_word_list_path)

    raise FileNotFoundError(
        "Could not find inline ## Word List section and fallback file is missing: "
        f"{fallback_word_list_path}"
    )


def extract_word_list(requirement_path: Path, fallback_word_list_path: Path) -> tuple[list[str], str]:
    """Extract deduplicated words and return (words, source_description)."""
    word_list_section, source_description = extract_word_list_source(
        requirement_path,
        fallback_word_list_path,
    )

    words: list[str] = []
    seen: set[str] = set()

    for line in word_list_section.split("\n"):
        line = line.strip()

        # Skip empty lines and comments.
        if not line or line.startswith("#"):
            continue

        # Remove bold markdown markers and optional bullet markers.
        line = line.replace("**", "")
        if line.startswith("-"):
            line = line[1:].strip()

        # Split on common separators to isolate source term.
        if ' – ' in line:
            word = line.split(' – ', 1)[0].strip()
        elif ' - ' in line:
            word = line.split(' - ', 1)[0].strip()
        elif ' = ' in line:
            word = line.split(' = ', 1)[0].strip()
        else:
            word = line.strip()

        word = re.sub(r'\s*\([^\)]*\)', '', word).strip()

        if not word:
            continue

        word_lower = word.lower()
        if word_lower not in seen:
            words.append(word)
            seen.add(word_lower)

    return words, source_description


def validate_no_template_placeholders(lines: list[str]) -> list[str]:
    """Reject template placeholders that should have been replaced with real content."""
    return validate_placeholder_values(lines)


def validate_no_generic_content(lines: list[str]) -> list[str]:
    """Reject generic/placeholder content that lacks real linguistic value."""
    issues: list[str] = []

    for field in iter_block_field_lines(lines):
        line_num = field.line_number
        field_name = field.field_name
        field_value = field.field_value
        if not field_value:
            continue

        # Check meaning field for generic markers.
        if field_name == "meaning":
            for marker in GENERIC_MEANING_MARKERS:
                if marker in field_value:
                    issues.append(
                        f"Line {line_num}: Generic meaning detected in '{field_name}' -> '{field_value}'"
                    )
                    break

        # Check de_1/en_1 for generic sentence patterns.
        full_line = f"{field_name}: {field_value}"
        for pattern in GENERIC_LINE_PATTERNS:
            if pattern.match(full_line):
                issues.append(
                    f"Line {line_num}: Generic example sentence in '{field_name}' -> '{field_value}'"
                )
                break

    return issues


def validate_noun_block_shape(lines: list[str]) -> list[str]:
    """Reject noun blocks that still look like phrases or sentence fragments."""
    issues: list[str] = []
    for block in iter_blocks(lines):
        fields: dict[str, tuple[int, str]] = {}
        for offset, raw_line in enumerate(block.body_lines, 1):
            line_number = block.start_line + offset
            stripped = raw_line.strip()
            if ": " not in stripped:
                continue
            field_name, field_value = stripped.split(": ", 1)
            fields[field_name] = (line_number, field_value.strip())

        tags = fields.get("Tags", (0, ""))[1]
        if tags != "noun":
            continue

        word_line, word_value = fields.get("word", (block.start_line, ""))
        word_inf_value = fields.get("word_inf", (block.start_line, ""))[1]
        tokens = word_value.split()

        if any(ch in word_value for ch in ("?", "!", "…")):
            issues.append(
                f"Line {word_line}: noun block word looks sentence-like -> '{word_value}'"
            )
            continue

        if len(tokens) > 1 and any(token and token[0].islower() for token in tokens[1:]):
            issues.append(
                f"Line {word_line}: noun block word looks like a phrase, not a noun lemma -> '{word_value}'"
            )
            continue

        if (
            len(tokens) == 1
            and tokens[0]
            and tokens[0][0].isupper()
            and word_inf_value.startswith("der ")
            and word_inf_value.removeprefix("der ").strip() == word_value
            and word_value.endswith(("e", "en"))
        ):
            issues.append(
                f"Line {word_line}: noun block likely guessed a bad masculine lemma -> '{word_value}' / '{word_inf_value}'"
            )

    return issues


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent.parent

    preferred_requirement_path = base_dir / "Requirement" / \
        "Requirement NW1 - German new words prompt.md"
    legacy_requirement_path = base_dir / "Requirement" / \
        "Requirement 1 - German new words prompt.md"

    preferred_vocab_path = base_dir / "Outputs" / "01_words.md"
    legacy_vocab_path = base_dir / "01_words.md"

    fallback_word_list_path = base_dir / "Inputs" / "Word List (DE).md"

    print("[INFO] Validating word list completeness...\n")

    req_result = resolve_with_legacy(
        preferred_requirement_path,
        legacy_requirement_path,
        "Requirement NW1",
    )
    for message in req_result.messages:
        print(message)

    if req_result.path is None:
        print("\n[ERROR] Validation failed: Requirement NW1 file not found.\n")
        return 1

    requirement_path = req_result.path

    vocab_result = resolve_with_legacy(
        preferred_vocab_path,
        legacy_vocab_path,
        "vocabulary output",
    )
    for message in vocab_result.messages:
        print(message)

    if vocab_result.path is None:
        print("\n[ERROR] Validation failed: vocabulary output file not found.\n")
        return 1

    vocab_path = vocab_result.path
    drift_detected = req_result.drift_detected or vocab_result.drift_detected

    try:
        word_list, source_desc = extract_word_list(
            requirement_path, fallback_word_list_path)
    except Exception as exc:
        print(f"[ERROR] Failed to extract word list: {exc}")
        return 1

    print(f"[INFO] Reading Word List from: {source_desc}")
    unique_count = len(word_list)
    print(f"   [OK] Found {unique_count} unique words/phrases\n")

    print(f"[INFO] Counting vocabulary blocks in: {vocab_path}")
    content = vocab_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    unresolved_words = extract_unresolved_words(lines)
    block_count, block_issues = analyze_block_structure(lines, label="vocabulary file")
    placeholder_issues = validate_no_template_placeholders(lines)
    word_hygiene_issues = validate_word_field_rules(lines)
    meaning_field_issues = validate_meaning_field_rules(lines)
    generic_content_issues = validate_no_generic_content(lines)
    required_field_issues = validate_required_core_fields(lines)
    tag_order_issues = validate_tags_last(lines)
    blank_line_issues = validate_no_blank_lines_between_fields(lines)
    duplicate_field_issues = validate_unique_fields_per_block(lines)
    noun_shape_issues = validate_noun_block_shape(lines)

    if block_issues:
        print("   [ERROR] Block indicator validation failed:")
        for issue in block_issues:
            print(f"      - {issue}")
    else:
        print(f"   [OK] Found {block_count} valid SSTART...EEND blocks\n")

    if placeholder_issues:
        print("   [ERROR] Placeholder validation failed:")
        for issue in placeholder_issues:
            print(f"      - {issue}")

    if word_hygiene_issues:
        print("   [ERROR] Word field hygiene validation failed:")
        for issue in word_hygiene_issues:
            print(f"      - {issue}")

    if meaning_field_issues:
        print("   [ERROR] Meaning field validation failed:")
        for issue in meaning_field_issues:
            print(f"      - {issue}")

    if generic_content_issues:
        print(
            "   [ERROR] Generic content detected (placeholder meanings/example sentences):")
        for issue in generic_content_issues:
            print(f"      - {issue}")

    if required_field_issues:
        print("   [ERROR] Missing/empty required core fields detected:")
        for issue in required_field_issues:
            print(f"      - {issue}")

    if tag_order_issues:
        print("   [ERROR] Tags field ordering validation failed:")
        for issue in tag_order_issues:
            print(f"      - {issue}")

    if blank_line_issues:
        print("   [ERROR] Blank line validation failed:")
        for issue in blank_line_issues:
            print(f"      - {issue}")

    if duplicate_field_issues:
        print("   [ERROR] Duplicate field validation failed:")
        for issue in duplicate_field_issues:
            print(f"      - {issue}")

    if noun_shape_issues:
        print("   [ERROR] Noun block shape validation failed:")
        for issue in noun_shape_issues:
            print(f"      - {issue}")

    print("[INFO] Comparison:")
    print(f"   Word List (Requirement NW1): {unique_count} unique entries")
    print(f"   Vocabulary Blocks: {block_count} entries")
    if unresolved_words:
        print(f"   Unresolved (explicit): {len(unresolved_words)} entries")

    expected_covered = unique_count - len(unresolved_words)

    allow_all_unresolved_empty_output = (
        unique_count > 0
        and expected_covered == 0
        and block_count == 0
        and block_issues
        and all("No SSTART...EEND blocks found" in issue for issue in block_issues)
        and not placeholder_issues
        and not word_hygiene_issues
        and not meaning_field_issues
        and not generic_content_issues
        and not required_field_issues
        and not tag_order_issues
        and not blank_line_issues
        and not duplicate_field_issues
        and not noun_shape_issues
        and not drift_detected
    )

    if block_count == expected_covered and not block_issues and not placeholder_issues and not word_hygiene_issues and not meaning_field_issues and not generic_content_issues and not required_field_issues and not tag_order_issues and not blank_line_issues and not duplicate_field_issues and not noun_shape_issues and not drift_detected:
        print(
            f"\n[OK] VALIDATION PASSED: {block_count} entries generated; {len(unresolved_words)} unresolved explicitly recorded."
        )
        print("   The generated vocabulary file is complete and path-consistent.\n")
        return 0

    if allow_all_unresolved_empty_output:
        print(
            f"\n[OK] VALIDATION PASSED: 0 entries generated; {len(unresolved_words)} unresolved explicitly recorded."
        )
        print("   All Word List items explicitly unresolved; empty output is permitted.\n")
        return 0

    if block_count > unique_count:
        print(
            f"\n[WARN] More blocks ({block_count}) than expected ({unique_count}).")
        print("   This may indicate duplicate entries or additional words.")
    elif block_count < unique_count:
        missing = unique_count - block_count
        print(f"\n[ERROR] VALIDATION FAILED: Missing {missing} entries.")
        print(f"   Expected: {unique_count} blocks (or {expected_covered} if unresolved accounted)")
        print(f"   Found: {block_count} blocks")
        if unresolved_words and block_count != expected_covered:
            print("   Unresolved list present, but counts still do not match expected coverage.")

    if drift_detected:
        print(
            "\n[ERROR] PATH DRIFT DETECTED: migrate files to preferred Outputs/ paths.")

    if block_issues:
        print(
            "\n[ERROR] BLOCK MARKER ERROR: replace any START...END markers with SSTART...EEND.")

    if placeholder_issues:
        print(
            "\n[ERROR] PLACEHOLDER ERROR: replace template placeholders with real content.")

    if word_hygiene_issues:
        print("\n[ERROR] WORD FIELD ERROR: remove parenthetical glosses from word: and avoid noun leading articles in word:.")

    if meaning_field_issues:
        print("\n[ERROR] MEANING FIELD ERROR: noun meanings must use article-bearing lemmas and must not define the noun with itself.")

    if generic_content_issues:
        print("\n[ERROR] GENERIC CONTENT ERROR: replace placeholder meanings and meta-sentences with real definitions and example sentences.")

    if required_field_issues:
        print("\n[ERROR] REQUIRED FIELDS ERROR: every block must include non-empty word, meaning, de_1, en_1, and Tags.")

    if tag_order_issues:
        print("\n[ERROR] TAGS ORDER ERROR: Tags must be the last field before EEND in every block.")

    if blank_line_issues:
        print("\n[ERROR] BLANK LINE ERROR: no empty lines are allowed between fields inside a block.")

    if duplicate_field_issues:
        print("\n[ERROR] DUPLICATE FIELD ERROR: each field and %VOCAB header may appear only once inside a block.")

    if noun_shape_issues:
        print("\n[ERROR] NOUN BLOCK ERROR: noun blocks must not contain phrase-like words or bad guessed singular lemmas.")

    print("\n   ACTION REQUIRED: fix issues and rerun validation.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
