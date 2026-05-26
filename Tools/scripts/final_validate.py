#!/usr/bin/env python3
"""
Simple validation for Requirement 4 - Check basic syntax compliance.

This validator enforces strict block indicators: SSTART...EEND.
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
    analyze_block_structure,
    find_noncanonical_reference_entries,
    iter_see_also_entries,
    looks_like_noun_candidate,
    resolve_with_legacy,
    validate_no_blank_lines_between_fields,
    validate_placeholder_values,
    validate_single_word_requires_see_also,
    validate_tags_last,
    validate_unique_fields_per_block,
    validate_word_field_rules,
)


CANONICAL_ENTRY_RE = re.compile(
    r"^(?:(?P<article>der|die|das|\([^)]+\))\s+)?\[(?P<term>[^|\]]+)\|nid\d+\]\s*=\s*.+$"
)


def find_noun_like_missing_articles(entries: list[str]) -> list[str]:
    """Return noun-like see_also entries that omit required der/die/das article."""
    issues: list[str] = []

    for entry in entries:
        match = CANONICAL_ENTRY_RE.match(entry)
        if not match:
            continue

        article = match.group("article")
        term = match.group("term")
        if article or not looks_like_noun_candidate(term):
            continue

        issues.append(entry)

    return issues


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent.parent
    preferred_path = base_dir / "Outputs" / "06_words_final_fixed.md"
    legacy_path = base_dir / "06_words_final_fixed.md"

    path_result = resolve_with_legacy(
        preferred_path,
        legacy_path,
        "validation target",
    )
    for message in path_result.messages:
        print(message)

    if path_result.path is None:
        return 1

    file_path = path_result.path
    drift_detected = path_result.drift_detected
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    print(f"[INFO] Final validation of {file_path}")
    print("=" * 50)

    _, block_issues = analyze_block_structure(lines)
    placeholder_issues = validate_placeholder_values(lines)
    if block_issues:
        print("[ERROR] Block indicator issues:")
        for issue in block_issues:
            print(f"  - {issue}")
    else:
        print("[OK] Block indicators are valid (SSTART...EEND)")

    if placeholder_issues:
        print("[ERROR] Placeholder issues:")
        for issue in placeholder_issues[:20]:
            print(f"  - {issue}")
        if len(placeholder_issues) > 20:
            print(f"  ... and {len(placeholder_issues) - 20} more")
    else:
        print("[OK] No unresolved template placeholders detected")

    non_phrase_issues = validate_single_word_requires_see_also(lines)
    word_field_issues = validate_word_field_rules(lines)
    tags_last_issues = validate_tags_last(lines)
    blank_line_issues = validate_no_blank_lines_between_fields(lines)
    duplicate_field_issues = validate_unique_fields_per_block(lines)

    if non_phrase_issues:
        print("[ERROR] Missing required see_also fields on non-phrase blocks:")
        for issue in non_phrase_issues[:20]:
            print(f"  - {issue}")
        if len(non_phrase_issues) > 20:
            print(f"  ... and {len(non_phrase_issues) - 20} more")
    else:
        print("[OK] All non-phrase blocks contain see_also entries")

    if word_field_issues:
        print("[ERROR] Invalid word field values detected:")
        for issue in word_field_issues[:20]:
            print(f"  - {issue}")
        if len(word_field_issues) > 20:
            print(f"  ... and {len(word_field_issues) - 20} more")
    else:
        print("[OK] Word fields follow required formatting rules")

    if tags_last_issues:
        print("[ERROR] Tags field ordering issues detected:")
        for issue in tags_last_issues[:20]:
            print(f"  - {issue}")
        if len(tags_last_issues) > 20:
            print(f"  ... and {len(tags_last_issues) - 20} more")
    else:
        print("[OK] Tags field is last before EEND in every block")

    if blank_line_issues:
        print("[ERROR] Blank line issues detected inside blocks:")
        for issue in blank_line_issues[:20]:
            print(f"  - {issue}")
        if len(blank_line_issues) > 20:
            print(f"  ... and {len(blank_line_issues) - 20} more")
    else:
        print("[OK] No blank lines appear between fields inside blocks")

    if duplicate_field_issues:
        print("[ERROR] Duplicate field/header issues detected inside blocks:")
        for issue in duplicate_field_issues[:20]:
            print(f"  - {issue}")
        if len(duplicate_field_issues) > 20:
            print(f"  ... and {len(duplicate_field_issues) - 20} more")
    else:
        print("[OK] No duplicate fields or duplicate %VOCAB headers appear inside blocks")

    see_also_entries = iter_see_also_entries(lines)
    nid_entries = re.findall(r"\[[^|\]]+\|nid(\d+)\]", "\n".join(see_also_entries))
    print(f"[OK] Found {len(nid_entries)} NID references")

    malformed = re.findall(r"nid[<>]", "\n".join(see_also_entries))
    if malformed:
        print(f"[ERROR] Found {len(malformed)} malformed NIDs with < or >")
    else:
        print("[OK] No malformed NIDs (all clean)")

    unmatched_brackets = find_noncanonical_reference_entries(see_also_entries)
    if unmatched_brackets:
        print(f"[ERROR] Found entries with non-canonical syntax: {len(unmatched_brackets)}")
    else:
        print("[OK] All entries follow canonical syntax")

    noun_like_missing_articles = find_noun_like_missing_articles(see_also_entries)
    if noun_like_missing_articles:
        print(
            "[ERROR] Found noun-like see_also entries without article "
            f"(expected der/die/das): {len(noun_like_missing_articles)}"
        )
        print("   Examples:")
        for entry in noun_like_missing_articles[:10]:
            print(f"   - {entry}")
        if len(noun_like_missing_articles) > 10:
            print(f"   ... and {len(noun_like_missing_articles) - 10} more")
    else:
        print("[OK] Noun-like see_also references include article markers")

    print("\nSample entries:")
    for index, entry in enumerate([e for e in see_also_entries if "|nid" in e][:5], 1):
        print(f"  {index}. {entry}")

    print("=" * 50)

    has_errors = bool(
        block_issues
        or placeholder_issues
        or non_phrase_issues
        or word_field_issues
        or tags_last_issues
        or blank_line_issues
        or duplicate_field_issues
        or malformed
        or unmatched_brackets
        or noun_like_missing_articles
        or drift_detected
    )
    if not has_errors:
        print("[OK] Requirement 4 validation PASSED! All syntax is correct.")
        print(f"[INFO] Summary: {len(nid_entries)} total NID references processed")
        return 0

    print("[WARN] Validation failed - please review issues above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
