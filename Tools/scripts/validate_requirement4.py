#!/usr/bin/env python3
"""
Final validation script for Requirement 4 - Check syntax compliance
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mdproc.validation_core import (
    extract_block_fields,
    find_noncanonical_reference_entries,
    iter_blocks,
    iter_see_also_entries,
    looks_like_noun_candidate,
    resolve_with_legacy,
    split_tags,
    validate_no_blank_lines_between_fields,
    validate_placeholder_values,
    validate_required_core_fields,
    validate_single_word_requires_see_also,
    validate_tags_last,
    validate_unique_fields_per_block,
    validate_word_field_rules,
    analyze_block_structure,
)


CORRECT_SEE_ALSO_RE = re.compile(
    r"^(?:(?:der|die|das|\([^)]+\))\s+)?\[[^|\]]+\|nid\d+\]\s*=\s*.+$"
)
FIELD_HEADER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*:")
MALFORMED_NID_RE = re.compile(r"nid[<>]\d+[<>]?")
BAD_GENDER_SPACING_RE = re.compile(r"\b(?:der|die|das)\[[^\]]+\|nid\d+\]")
ENTRY_PARSE_RE = re.compile(
    r"^(?:(?P<article>der|die|das|\([^)]+\))\s+)?\[(?P<term>[^|\]]+)\|nid\d+\]\s*=\s*.+$"
)
ASCII_TRANSLIT_RE = re.compile(r"(?i)(?<![aeiouyäöü])(?:ae|oe|ue)")
NON_TRANSLIT_WORD_RE = re.compile(
    r"(?i)^(?:bequem|neu(?:e|en|em|er|es)?|heute|leute|kunde(?:n|m|r|s)?|eventuell|aktuell|manuell|individuell)$"
)
GERMAN_TEXT_FIELDS = {
    "word",
    "meaning",
    "de_1",
    "word_inf",
    "noun_gender",
    "noun_genetiv",
    "noun_plural",
    "verb_present",
    "verb_past",
    "verb_perfect",
}


def validate_see_also_syntax(file_path: Path) -> tuple[int, list[str]]:
    """Validate that all see_also entries follow the correct syntax."""
    lines = file_path.read_text(encoding="utf-8").splitlines()
    return validate_see_also_syntax_from_lines(lines)


def validate_see_also_syntax_from_lines(lines: list[str]) -> tuple[int, list[str]]:
    """Validate canonical see_also entry syntax from input lines."""
    issues: list[str] = []
    valid_entries = 0

    for block in iter_blocks(lines):
        for entry in iter_see_also_entries(block.body_lines):
            if CORRECT_SEE_ALSO_RE.match(entry):
                valid_entries += 1
            else:
                issues.append(
                    f"Line {find_entry_line(block, entry)}: Invalid syntax - '{entry}'"
                )

    return valid_entries, issues


def find_entry_line(block, entry: str) -> int:
    """Return source line number for a see_also entry within a block."""
    for offset, raw in enumerate(block.body_lines, 1):
        if raw.strip() == entry:
            return block.start_line + offset
    return block.start_line


def _strip_article(value: str) -> str:
    text = value.strip()
    for article in ("der ", "die ", "das ", "des ", "dem ", "den "):
        if text.startswith(article):
            return text[len(article):].strip()
    return text


def _umlaut_variants(word: str) -> list[str]:
    variants = set()
    chars = list(word)

    for i in range(len(chars) - 1):
        if chars[i] == "a" and chars[i + 1] == "u":
            variant = chars.copy()
            variant[i] = "ä"
            variants.add("".join(variant))

    for i in range(len(chars) - 1, -1, -1):
        if chars[i] in ("a", "o", "u"):
            variant = chars.copy()
            variant[i] = {"a": "ä", "o": "ö", "u": "ü"}[chars[i]]
            variants.add("".join(variant))

    return sorted(variants)


def _derive_genitive_form(lemma: str, noun_genetiv: str) -> str:
    genitive = _strip_article(noun_genetiv)
    if not genitive or genitive == "-":
        return ""
    if genitive == lemma:
        return "-"
    if genitive == lemma + "s":
        return "-s"
    if genitive == lemma + "es":
        return "-es"
    if genitive == lemma + "n":
        return "-n"
    if genitive == lemma + "en":
        return "-en"
    return "?"


def _derive_plural_form(lemma: str, noun_plural: str) -> str:
    plural = noun_plural.strip()
    if not plural or plural == "-":
        return ""
    if plural == lemma:
        return "-"
    if plural == lemma + "n":
        return "-n"
    if plural == lemma + "en":
        return "-en"
    if plural == lemma + "e":
        return "-e"
    if plural == lemma + "er":
        return "-er"
    if plural == lemma + "s":
        return "-s"

    for base in _umlaut_variants(lemma):
        if plural == base:
            return "⸚"
        if plural == base + "e":
            return "⸚e"
        if plural == base + "er":
            return "⸚er"

    return "?"


def validate_blank_fields_and_noun_forms(file_path: Path, lines: list[str] | None = None) -> list[str]:
    """Reject blank fields and verify noun_forms consistency."""
    if lines is None:
        lines = file_path.read_text(encoding="utf-8").splitlines()

    issues: list[str] = []
    for block in iter_blocks(lines):
        values, line_numbers = extract_block_fields(block)
        tags = split_tags(values.get("Tags", ""))
        is_noun = "noun" in tags

        noun_forms_value = values.get("noun_forms")
        noun_forms_line = line_numbers.get("noun_forms")
        noun_tag_line = line_numbers.get("Tags", block.start_line)

        for field_name, field_value in values.items():
            if field_name != "see_also" and field_value in {"", "-"}:
                issues.append(
                    f"Line {line_numbers[field_name]}: Blank field should be removed - '{field_name}: {field_value}'"
                )

        if noun_forms_value is not None:
            if not is_noun and noun_forms_value:
                issues.append(
                    f"Line {noun_forms_line}: noun_forms must be empty for non-noun blocks"
                )
            if is_noun:
                if "," not in noun_forms_value:
                    issues.append(
                        f"Line {noun_forms_line}: noun_forms must use 'genitive, plural' format (e.g., '-s, -e' or '-s,')"
                    )
                else:
                    left, right = noun_forms_value.split(",", 1)
                    actual_genitive = left.strip()
                    actual_plural = right.strip()
                    lemma = _strip_article(values.get("word_inf", ""))
                    expected_genitive = _derive_genitive_form(
                        lemma, values.get("noun_genetiv", "")
                    )
                    expected_plural = _derive_plural_form(
                        lemma, values.get("noun_plural", "")
                    )

                    if expected_genitive != "?" and expected_plural != "?":
                        expected_text = (
                            f"{expected_genitive}, {expected_plural}"
                            if expected_plural
                            else f"{expected_genitive},"
                        )
                        if (
                            actual_genitive != expected_genitive
                            or actual_plural != expected_plural
                        ):
                            issues.append(
                                f"Line {noun_forms_line}: noun_forms '{noun_forms_value}' does not match expected '{expected_text}'"
                            )
        elif is_noun:
            issues.append(
                f"Line {noun_tag_line}: missing noun_forms field for noun block"
            )

    return issues


def _translit_issue_text(value: str) -> str:
    for word in re.findall(r"[A-Za-zÄÖÜäöüß]+", value):
        if NON_TRANSLIT_WORD_RE.match(word):
            continue
        lower_word = word.lower()
        match = ASCII_TRANSLIT_RE.search(word)
        if match:
            if match.group(0).lower() == "ue" and match.start() == 1 and lower_word.startswith("zue"):
                continue
            return f"contains ASCII transliteration '{match.group(0)}'"
    return ""


def validate_german_diacritics(lines: list[str]) -> list[str]:
    """Detect ASCII transliterations in German-facing fields and see_also terms."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        in_see_also = False
        for offset, raw in enumerate(block.body_lines, 1):
            stripped = raw.strip()
            line_number = block.start_line + offset

            if stripped == "see_also:":
                in_see_also = True
                continue

            if in_see_also:
                if stripped and FIELD_HEADER_RE.match(stripped):
                    in_see_also = False
                elif stripped:
                    lhs = stripped.split("=", 1)[0].strip()
                    terms = re.findall(r"\[([^|\]]+)\|nid\d+\]", lhs)
                    for term in terms:
                        detail = _translit_issue_text(term)
                        if detail:
                            issues.append(
                                f"Line {line_number}: {detail} in see_also term '{term}'"
                            )
                    continue

            if ":" not in stripped:
                continue

            field_name, field_value = stripped.split(":", 1)
            field_name = field_name.strip()
            field_value = field_value.strip()
            if field_name not in GERMAN_TEXT_FIELDS:
                continue

            text_to_check = field_value.split(" / ", 1)[0].strip() if field_name == "meaning" else field_value
            detail = _translit_issue_text(text_to_check)
            if detail:
                issues.append(
                    f"Line {line_number}: {detail} in field '{field_name}' -> '{field_value}'"
                )

    return issues


def validate_noun_articles_in_see_also(lines: list[str]) -> list[str]:
    """Require article markers for noun-like see_also terms."""
    issues: list[str] = []

    for block in iter_blocks(lines):
        for entry in iter_see_also_entries(block.body_lines):
            match = ENTRY_PARSE_RE.match(entry)
            if not match:
                continue

            article = match.group("article")
            term = match.group("term")
            if article or not looks_like_noun_candidate(term):
                continue

            issues.append(
                f"Line {find_entry_line(block, entry)}: noun-like see_also term '{term}' is missing article (expected der/die/das)"
            )

    return issues


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent.parent
    preferred_file_path = base_dir / "Outputs" / "06_words_final_fixed.md"
    legacy_file_path = base_dir / "06_words_final_fixed.md"

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")

    path_result = resolve_with_legacy(
        preferred_file_path,
        legacy_file_path,
        "validation target",
    )
    for message in path_result.messages:
        print(message)

    if path_result.path is None:
        return 1

    file_path = path_result.path
    drift_detected = path_result.drift_detected
    print(f"[INFO] Validating see_also syntax in {file_path}...")
    print("=" * 60)

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    valid_entries, syntax_issues = validate_see_also_syntax_from_lines(lines)
    _, block_issues = analyze_block_structure(lines)
    blank_field_issues = validate_blank_fields_and_noun_forms(file_path, lines)
    translit_issues = validate_german_diacritics(lines)
    noun_article_issues = validate_noun_articles_in_see_also(lines)
    placeholder_issues = validate_placeholder_values(lines)
    single_word_issues = validate_single_word_requires_see_also(lines)
    word_field_issues = validate_word_field_rules(lines)
    required_field_issues = validate_required_core_fields(lines)
    tag_order_issues = validate_tags_last(lines)
    blank_line_issues = validate_no_blank_lines_between_fields(lines)
    duplicate_field_issues = validate_unique_fields_per_block(lines)

    all_issues = (
        syntax_issues
        + block_issues
        + blank_field_issues
        + translit_issues
        + noun_article_issues
        + placeholder_issues
        + single_word_issues
        + word_field_issues
        + required_field_issues
        + tag_order_issues
        + blank_line_issues
        + duplicate_field_issues
    )

    if all_issues:
        print(f"[ERROR] Found {len(all_issues)} validation issues:")
        for issue in all_issues:
            print(f"  {issue}")
    else:
        print(f"[OK] All {valid_entries} see_also entries have valid syntax!")

    print("=" * 60)
    print("[INFO] Checking specific requirements:")

    see_also_entries = iter_see_also_entries(lines)
    malformed_nids = MALFORMED_NID_RE.findall("\n".join(see_also_entries))
    if malformed_nids:
        print(f"[ERROR] Found malformed NIDs: {malformed_nids}")
    else:
        print("[OK] All NIDs are clean (no < > characters)")

    noncanonical_entries = find_noncanonical_reference_entries(see_also_entries)
    if noncanonical_entries:
        print(f"[ERROR] Found entries with non-canonical syntax: {noncanonical_entries}")
    else:
        print("[OK] All entries follow canonical syntax")

    bad_gender_spacing = [
        entry for entry in see_also_entries if BAD_GENDER_SPACING_RE.search(entry)
    ]
    if bad_gender_spacing:
        print(f"[ERROR] Found incorrect gender spacing: {bad_gender_spacing}")
    else:
        print("[OK] All gender markers have correct spacing")

    print("=" * 60)
    if not (
        all_issues
        or malformed_nids
        or noncanonical_entries
        or bad_gender_spacing
        or drift_detected
    ):
        print("[OK] Requirement 4 validation PASSED! All syntax is correct.")
        return 0

    print("[WARN] Some issues found - please review above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
