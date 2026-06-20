#!/usr/bin/env python3
"""
Requirement 4: Validate and Normalize see_also Anki References

This script processes Outputs/06_words_final.md and normalizes all see_also field entries
to ensure they follow the canonical syntax: ([gender]) [related_word|nid<anki_note_id>].
It enforces strict block markers SSTART...EEND and rejects legacy START...END.
"""

import re
import sys
from pathlib import Path


BLOCK_START = "SSTART"
BLOCK_END = "EEND"
LEGACY_BLOCK_START = "START"
LEGACY_BLOCK_END = "END"

GERMAN_FIELDS = {
    "word",
    "meaning",
    "de_1",
    "word_inf",
    "noun_genetiv",
    "noun_plural",
    "adjective_comp",
    "adjective_sup",
    "verb_praet",
    "verb_perf",
}
BACKFILL_FIELDS = ("de_1", "en_1", "word_inf", "noun_gender", "noun_genetiv", "noun_plural")
NOUN_ONLY_FIELDS = {"noun_gender", "noun_genetiv", "noun_plural", "noun_forms"}
SOURCE_OVERRIDE_FIELDS = {"meaning", "de_1", "en_1", "word_inf", "noun_gender", "noun_genetiv", "noun_plural", "Tags"}
VOCAB_HEADER_LINES = {"%VOCAB (German) ver 3", "VOCAB (German) ver 3"}


def resolve_with_legacy(preferred: Path, legacy: Path, label: str) -> tuple[Path | None, list[str], bool]:
    """Resolve preferred path with legacy fallback and drift warnings."""
    messages: list[str] = []
    drift_detected = False

    if preferred.exists() and legacy.exists():
        drift_detected = True
        messages.append(
            f"[WARN] Path drift detected for {label}: both preferred and legacy files exist.")
        messages.append(f"   Preferred: {preferred}")
        messages.append(f"   Legacy:    {legacy}")
        return preferred, messages, drift_detected

    if preferred.exists():
        return preferred, messages, drift_detected

    if legacy.exists():
        drift_detected = True
        messages.append(
            f"[WARN] Path drift detected for {label}: using legacy path.")
        messages.append(f"   Expected: {preferred}")
        messages.append(f"   Legacy:   {legacy}")
        return legacy, messages, drift_detected

    messages.append(f"[ERROR] Missing {label} file: {preferred}")
    messages.append(f"   Legacy path also missing: {legacy}")
    return None, messages, drift_detected


def analyze_block_indicators(lines: list[str]) -> list[str]:
    """Validate strict block markers and reject START...END."""
    content = "\n".join(lines)
    sstart_count = len(re.findall(r'^\s*SSTART\s*$', content, re.MULTILINE))
    eend_count = len(re.findall(r'^\s*EEND\s*$', content, re.MULTILINE))
    legacy_start_count = len(re.findall(
        r'^\s*START\s*$', content, re.MULTILINE))
    legacy_end_count = len(re.findall(r'^\s*END\s*$', content, re.MULTILINE))

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
        issues.append("No SSTART...EEND blocks found in input file.")

    return issues


def normalize_see_also_entry(line: str) -> str:
    """
    Normalize a single see_also entry line.

    Expected format: ([gender]) [related_word|nid<anki_note_id>] = meaning
    """
    line = line.strip()

    # Skip empty lines or lines that don't contain references
    if not line or '|nid' not in line:
        return line

    # Pattern to match the see_also entry structure
    # Captures: optional gender, word, nid, optional meaning
    pattern = r'^((?:der|die|das|\([^)]+\))?\s*)?(\[?)([^|\]]+)\|nid([<>]?)(\d+)([<>]?)(\]?)(.*)$'

    match = re.match(pattern, line)
    if not match:
        return line  # Return unchanged if pattern doesn't match

    gender, left_bracket, word, nid_prefix, nid_num, nid_suffix, right_bracket, meaning = match.groups()

    # Normalize gender part
    if gender:
        gender = gender.strip()
        if not gender.endswith(' '):
            gender += ' '
    else:
        gender = ''

    # Ensure proper bracketing
    if not left_bracket:
        left_bracket = '['
    if not right_bracket:
        right_bracket = ']'

    # Clean up NID - remove < and > characters
    clean_nid = nid_num

    # Reconstruct the normalized entry
    normalized = f"{gender}[{word}|nid{clean_nid}]{meaning}"

    return normalized


def _is_field_line(stripped_line: str) -> bool:
    if not stripped_line or ":" not in stripped_line:
        return False
    field_name = stripped_line.split(":", 1)[0].strip()
    return bool(field_name)


def _is_noun_block(block_lines: list[str]) -> bool:
    tags_value = _extract_block_fields(block_lines).get("Tags", "").lower()
    tags_tokens = re.split(r"[\s,]+", tags_value)
    return "noun" in {token for token in tags_tokens if token}


def _is_blank_field(field_name: str, field_value: str) -> bool:
    if field_name == "see_also":
        return False
    normalized_value = field_value.strip()
    return normalized_value == "" or normalized_value == "-"


def _extract_block_fields(block_lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block_lines[1:-1]:
        stripped = line.strip()
        if not _is_field_line(stripped):
            continue
        field_name, field_value = stripped.split(":", 1)
        fields[field_name.strip()] = field_value.strip()
    return fields


def _count_block_fields(block_lines: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in block_lines[1:-1]:
        stripped = line.strip()
        if not _is_field_line(stripped):
            continue
        field_name = stripped.split(":", 1)[0].strip()
        counts[field_name] = counts.get(field_name, 0) + 1
    return counts


def _build_source_field_map(source_path: Path) -> dict[str, dict[str, str]]:
    if not source_path.exists():
        return {}

    lines = source_path.read_text(encoding="utf-8").splitlines(keepends=True)
    mapping: dict[str, dict[str, str]] = {}
    i = 0
    while i < len(lines):
        if lines[i].strip() != BLOCK_START:
            i += 1
            continue

        j = i + 1
        while j < len(lines) and lines[j].strip() != BLOCK_END:
            j += 1
        if j >= len(lines):
            break

        fields = _extract_block_fields(lines[i: j + 1])
        word = fields.get("word", "").strip().lower()
        if word:
            mapping[word] = fields
        i = j + 1

    return mapping


def _normalize_umlauts(text: str) -> str:
    replacements = (
        ("Ae", "Ä"),
        ("Oe", "Ö"),
        ("Ue", "Ü"),
        ("ae", "ä"),
        ("oe", "ö"),
        ("ue", "ü"),
    )
    out = text
    for src, dst in replacements:
        out = out.replace(src, dst)
    return out


def _normalize_german_field(field_name: str, field_value: str) -> str:
    if field_name not in GERMAN_FIELDS:
        return field_value

    if field_name == "meaning":
        # meaning uses "German / English"; normalize only German side.
        if " / " in field_value:
            left, right = field_value.split(" / ", 1)
            return f"{_normalize_umlauts(left)} / {right}"
        return _normalize_umlauts(field_value)

    return _normalize_umlauts(field_value)


def _strip_article(value: str) -> str:
    text = value.strip()
    for article in ("der ", "die ", "das ", "des ", "dem ", "den "):
        if text.startswith(article):
            return text[len(article):].strip()
    return text


def _derive_genitive_form(lemma: str, noun_genetiv: str) -> str:
    gen = _strip_article(noun_genetiv)
    if not gen or gen == "-":
        return ""
    if gen == lemma:
        return "-"
    if gen == lemma + "s":
        return "-s"
    if gen == lemma + "es":
        return "-es"
    if gen == lemma + "n":
        return "-n"
    if gen == lemma + "en":
        return "-en"
    return "?"


def _derive_plural_form(lemma: str, noun_plural: str) -> str:
    pl = noun_plural.strip()
    if not pl or pl == "-":
        return ""
    if pl == lemma:
        return "-"
    if pl == lemma + "n":
        return "-n"
    if pl == lemma + "en":
        return "-en"
    if pl == lemma + "e":
        return "-e"
    if pl == lemma + "er":
        return "-er"
    if pl == lemma + "s":
        return "-s"
    for base in _umlaut_variants(lemma):
        if pl == base:
            return "⸚"
        if pl == base + "e":
            return "⸚e"
        if pl == base + "er":
            return "⸚er"
    return "?"


def _umlaut_variants(word: str) -> list[str]:
    variants: set[str] = set()
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


def _derive_noun_forms(word_inf: str, noun_genetiv: str, noun_plural: str) -> str:
    lemma = _strip_article(word_inf)
    if not lemma:
        return ","

    gen = _derive_genitive_form(lemma, noun_genetiv)
    pl = _derive_plural_form(lemma, noun_plural)

    if gen == "?":
        gen = ""
    if pl == "?":
        pl = ""

    return f"{gen}, {pl}" if pl else f"{gen},"


def _normalize_requirement4_block(block_lines: list[str], source_fields: dict[str, str] | None = None) -> list[str]:
    if len(block_lines) < 2:
        return block_lines

    existing_fields = _extract_block_fields(block_lines)
    field_counts = _count_block_fields(block_lines)
    duplicate_vocab_headers = sum(
        1 for line in block_lines[1:-1] if line.strip() in VOCAB_HEADER_LINES
    )
    has_duplicate_fields = any(count > 1 for count in field_counts.values())
    source_tags = (source_fields or {}).get("Tags", "").strip().lower()
    if duplicate_vocab_headers > 1 or has_duplicate_fields:
        is_noun = "noun" in {token for token in re.split(r"[\s,]+", source_tags) if token}
    else:
        is_noun = _is_noun_block(block_lines)
    pending_backfill: list[str] = []
    for field_name in BACKFILL_FIELDS:
        source_value = (source_fields or {}).get(field_name, "").strip()
        current_value = existing_fields.get(field_name, "").strip()
        if source_value and not _is_blank_field(field_name, source_value) and _is_blank_field(field_name, current_value):
            normalized_source_value = _normalize_german_field(field_name, source_value)
            pending_backfill.append(f"{field_name}: {normalized_source_value}\n")

    result: list[str] = [block_lines[0], "%VOCAB (German) ver 3\n"]
    in_see_also = False
    inserted_backfill = False
    emitted_fields: set[str] = set()
    word_inf = ""
    noun_genetiv = ""
    noun_plural = ""
    tags_line: str | None = None
    source_tags = (source_fields or {}).get("Tags", "").strip()
    pending_tags_line = (
        f"Tags: {_normalize_german_field('Tags', source_tags)}\n"
        if source_tags and not _is_blank_field("Tags", source_tags)
        else None
    )

    for line in block_lines[1:-1]:
        raw = line.rstrip("\n\r")
        stripped = raw.strip()

        if stripped in VOCAB_HEADER_LINES:
            continue

        if stripped == "see_also:":
            if pending_backfill and not inserted_backfill:
                result.extend(pending_backfill)
                inserted_backfill = True
            in_see_also = True
            result.append("see_also:\n")
            continue

        if in_see_also:
            if _is_field_line(stripped):
                in_see_also = False
            elif stripped:
                result.append(normalize_see_also_entry(raw) + "\n")
                continue
            else:
                continue

        if _is_field_line(stripped):
            field_name, field_value = stripped.split(":", 1)
            field_name = field_name.strip()
            field_value = field_value.strip()

            if field_name in NOUN_ONLY_FIELDS and not is_noun:
                continue

            if _is_blank_field(field_name, field_value):
                continue

            if field_name == "noun_forms":
                # Recompute noun_forms from source noun fields for nouns.
                # Drop stale/manual noun_forms lines to keep output deterministic.
                continue

            if field_name in existing_fields and field_value != existing_fields[field_name]:
                continue
            if field_name in emitted_fields:
                continue

            if field_name in SOURCE_OVERRIDE_FIELDS:
                source_value = (source_fields or {}).get(field_name, "").strip()
                if source_value and not _is_blank_field(field_name, source_value):
                    field_value = source_value

            normalized_value = _normalize_german_field(field_name, field_value)

            if field_name == "word_inf":
                word_inf = normalized_value
            elif field_name == "noun_genetiv":
                noun_genetiv = normalized_value
            elif field_name == "noun_plural":
                noun_plural = normalized_value

            line_text = f"{field_name}: {normalized_value}\n"
            if field_name == "Tags":
                tags_line = line_text
            else:
                result.append(line_text)
            emitted_fields.add(field_name)
            continue

        if stripped:
            result.append(raw.rstrip() + "\n")

    if pending_backfill and not inserted_backfill:
        result.extend(pending_backfill)

    if is_noun:
        effective_word_inf = word_inf or _normalize_german_field(
            "word_inf", (source_fields or {}).get("word_inf", "")
        )
        effective_noun_genetiv = noun_genetiv or _normalize_german_field(
            "noun_genetiv", (source_fields or {}).get("noun_genetiv", "")
        )
        effective_noun_plural = noun_plural or _normalize_german_field(
            "noun_plural", (source_fields or {}).get("noun_plural", "")
        )
        inferred_noun_forms = _derive_noun_forms(
            effective_word_inf, effective_noun_genetiv, effective_noun_plural)
        result.append(f"noun_forms: {inferred_noun_forms}\n")

    if tags_line is not None:
        result.append(tags_line)
    elif pending_tags_line is not None:
        result.append(pending_tags_line)

    result.append(block_lines[-1])
    return result


def _cleanup_non_noun_noun_forms(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() != BLOCK_START:
            cleaned.append(lines[i])
            i += 1
            continue

        j = i + 1
        while j < len(lines) and lines[j].strip() != BLOCK_END:
            j += 1
        if j >= len(lines):
            cleaned.extend(lines[i:])
            break

        block = lines[i: j + 1]
        if not _is_noun_block(block):
            block = [
                line for line in block
                if not line.strip().startswith("noun_forms:")
            ]
        cleaned.extend(block)
        i = j + 1

    return cleaned


def process_markdown_file(
    input_path: str | Path,
    output_path: str | Path,
    source_fields_by_word: dict[str, dict[str, str]] | None = None,
) -> None:
    """
    Process markdown and normalize see_also plus Requirement 4 field checks.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    block_issues = analyze_block_indicators(lines)
    if block_issues:
        issue_text = "\n".join(f"- {issue}" for issue in block_issues)
        raise ValueError(f"Block indicator validation failed:\n{issue_text}")

    processed_lines = []
    i = 0

    while i < len(lines):
        if lines[i].strip() == BLOCK_START:
            j = i + 1
            while j < len(lines) and lines[j].strip() != BLOCK_END:
                j += 1

            if j < len(lines):
                block = lines[i: j + 1]
                fields = _extract_block_fields(block)
                source_fields = source_fields_by_word.get(
                    fields.get("word", "").strip().lower(), {}
                ) if source_fields_by_word else {}
                processed_lines.extend(_normalize_requirement4_block(block, source_fields))
                i = j + 1
                continue

            # Unclosed block: keep original line and continue.
            processed_lines.append(lines[i])
            i += 1
        else:
            processed_lines.append(lines[i])
            i += 1

    processed_lines = _cleanup_non_noun_noun_forms(processed_lines)

    # Write the processed content to the output file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(processed_lines)

    print(f"Processed file saved to: {output_path}")


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent.parent
    preferred_input = base_dir / "Outputs" / "06_words_final.md"
    legacy_input = base_dir / "06_words_final.md"

    input_file, path_messages, drift_detected = resolve_with_legacy(
        preferred_input,
        legacy_input,
        "Requirement NW4 input",
    )
    for message in path_messages:
        print(message)

    if input_file is None:
        return 1

    output_file = base_dir / "Outputs" / "06_words_final_fixed.md"
    source_fields_by_word = _build_source_field_map(base_dir / "Outputs" / "01_words.md")

    if drift_detected:
        print("[WARN] Continue after resolving path drift if possible.")

    try:
        process_markdown_file(input_file, output_file, source_fields_by_word)
        print("[OK] Requirement 4 completed successfully!")
        print(f"[OK] Normalized see_also entries in {output_file}")
        return 0
    except Exception as e:
        print(f"[ERROR] Error processing file: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
