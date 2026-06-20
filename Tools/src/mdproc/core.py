from __future__ import annotations

import re
from typing import Iterable, List


BLOCK_START = "SSTART"
BLOCK_END = "EEND"

FIELD_LINE_RE = re.compile(r"^([%]?[A-Za-z_][A-Za-z0-9_]*)\s*:(.*)$")
TAG_PUNCT_RE = re.compile(r"[(),:;=\-*+.`~\"'?>|\[\]{}\\/]")
ARTICLE_RE = re.compile(
    r"^(?:der|die|das|ein|eine|des|dem|den)\s+", re.IGNORECASE)


def process_markdown(md: str) -> str:
    """Return normalized markdown per requirements."""
    lines = md.splitlines()
    result_lines: list[str] = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == BLOCK_START:
            block_end = _find_block_end(lines, i + 1)
            if block_end is None:
                result_lines.append(lines[i].rstrip())
                i += 1
                continue
            result_lines.extend(_normalize_block(lines[i: block_end + 1]))
            i = block_end + 1
            continue

        result_lines.append(lines[i].rstrip())
        i += 1

    return _join_lines(result_lines, md.endswith("\n"))


def extract_words(md: str) -> list[str]:
    """Return deduplicated WORD list in source order."""
    lines = md.splitlines()
    words: list[str] = []
    seen: set[str] = set()
    i = 0

    while i < len(lines):
        if lines[i].strip() == BLOCK_START:
            block_end = _find_block_end(lines, i + 1)
            if block_end is None:
                i += 1
                continue

            word = _extract_word_from_block(lines[i + 1: block_end])
            if word:
                key = word.casefold()
                if key not in seen:
                    seen.add(key)
                    words.append(word)
            i = block_end + 1
            continue

        i += 1

    return words


def preprocess_file1(md: str) -> str:
    """Deduplicate by WORD (keep first), normalize whitespace for File 1."""
    lines = md.splitlines()
    result_lines: list[str] = []
    seen_words: set[str] = set()
    i = 0

    while i < len(lines):
        if lines[i].strip() == BLOCK_START:
            block_end = _find_block_end(lines, i + 1)
            if block_end is None:
                result_lines.append(lines[i].rstrip())
                i += 1
                continue

            block = lines[i: block_end + 1]
            word = _extract_word_from_block(block[1:-1])
            if word and word.casefold() not in seen_words:
                seen_words.add(word.casefold())
                result_lines.extend(_normalize_block(block))
            i = block_end + 1
            continue

        result_lines.append(lines[i].rstrip())
        i += 1

    return _join_lines(result_lines, md.endswith("\n"))


def merge_see_also(file1_md: str, file2_md: str) -> str:
    """Inject see_also from File 1 into matching WORD blocks in File 2."""
    see_also_data = _extract_see_also_from_file1(file1_md)
    lines = file2_md.splitlines()
    result_lines: list[str] = []
    i = 0

    while i < len(lines):
        if lines[i].strip() != BLOCK_START:
            result_lines.append(lines[i].rstrip())
            i += 1
            continue

        block_end = _find_block_end(lines, i + 1)
        if block_end is None:
            result_lines.append(lines[i].rstrip())
            i += 1
            continue

        block = lines[i: block_end + 1]
        word = _extract_word_from_block(block[1:-1])
        merged_block = _merge_see_also_into_block(
            block, see_also_data.get(_casefold(word)))
        result_lines.extend(merged_block)
        i = block_end + 1

    return _join_lines(result_lines, file2_md.endswith("\n"))


def _join_lines(lines: list[str], trailing_newline: bool) -> str:
    text = "\n".join(line.rstrip() for line in lines)
    return text + ("\n" if trailing_newline else "")


def _casefold(value: str | None) -> str:
    return value.casefold() if value else ""


def _find_block_end(lines: List[str], start_idx: int) -> int | None:
    for idx in range(start_idx, len(lines)):
        if lines[idx].strip() == BLOCK_END:
            return idx
    return None


def _extract_word_from_block(block_lines: Iterable[str]) -> str | None:
    for line in block_lines:
        stripped = line.strip()
        match = FIELD_LINE_RE.match(stripped)
        if not match:
            continue
        field_name = match.group(1).lstrip("%")
        if field_name.lower() == "word":
            return match.group(2).strip()
    return None


def _normalize_block(block_lines: List[str]) -> List[str]:
    if len(block_lines) < 2:
        return [line.rstrip() for line in block_lines]

    result: list[str] = [BLOCK_START]
    inner = block_lines[1:-1]
    normalized_inner: list[str] = []

    i = 0
    while i < len(inner):
        raw = inner[i].rstrip()
        stripped = raw.strip()

        if not stripped:
            normalized_inner.append("")
            i += 1
            continue

        if stripped == "see_also:":
            normalized_inner.append("see_also:")
            i += 1
            while i < len(inner):
                candidate = inner[i].rstrip()
                candidate_stripped = candidate.strip()
                if not candidate_stripped:
                    i += 1
                    continue
                if _is_field_line(candidate_stripped):
                    break
                normalized_inner.append(candidate_stripped)
                i += 1
            continue

        if _is_field_line(stripped):
            normalized_inner.append(_normalize_field_line(stripped))
        else:
            normalized_inner.append(_collapse_spaces(raw))
        i += 1

    normalized_inner = _remove_excessive_blank_lines(normalized_inner)
    result.extend(normalized_inner)
    result.append(BLOCK_END)
    return result


def _normalize_field_line(line: str) -> str:
    match = FIELD_LINE_RE.match(line)
    if not match:
        return line.rstrip()

    field_name = match.group(1).lstrip("%").strip()
    field_value = _collapse_spaces(match.group(2).strip())
    field_name_lower = field_name.lower()

    if field_name_lower == "tags":
        field_name = "Tags"
        field_value = _normalize_tags_field(field_value)
    elif field_name_lower == "noun_gender":
        field_value = _normalize_gender_field(field_value)
    elif field_name_lower == "see_also":
        field_name = "see_also"
        field_value = ""

    return f"{field_name}: {field_value}".rstrip()


def _normalize_gender_field(value: str) -> str:
    return re.sub(r"\((Plural|Pluralwort)\)", "(plural)", value, flags=re.IGNORECASE)


def _normalize_tags_field(value: str) -> str:
    value = TAG_PUNCT_RE.sub(" ", value)
    token_map = {
        "adjective": "adj",
        "adverb": "adv",
        "conjunction": "conj",
        "preposition": "prep",
    }
    allowlist = {
        "verb",
        "noun",
        "adj",
        "adv",
        "sentence",
        "phrase",
        "conj",
        "compound",
        "interjection",
        "modal",
        "possessive",
        "prefix",
        "prep",
        "pronoun",
    }

    normalized: list[str] = []
    seen: set[str] = set()
    for token in value.split():
        mapped = token_map.get(token.casefold(), token.casefold())
        if mapped in allowlist and mapped not in seen:
            seen.add(mapped)
            normalized.append(mapped)

    normalized.sort()
    return " ".join(normalized)


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _remove_excessive_blank_lines(lines: List[str]) -> List[str]:
    if not lines:
        return lines

    result: list[str] = []
    blank_seen = False
    for line in lines:
        if line.strip() == "":
            if not blank_seen:
                result.append("")
                blank_seen = True
            continue
        blank_seen = False
        result.append(line.rstrip())

    while result and result[-1] == "":
        result.pop()
    return result


def _extract_see_also_from_file1(md: str) -> dict[str, list[str]]:
    lines = md.splitlines()
    data: dict[str, list[str]] = {}
    i = 0

    while i < len(lines):
        if lines[i].strip() != BLOCK_START:
            i += 1
            continue

        block_end = _find_block_end(lines, i + 1)
        if block_end is None:
            i += 1
            continue

        block = lines[i + 1: block_end]
        word = _extract_word_from_block(block)
        items = _extract_see_also_from_block(block)
        if word and items:
            data[word.casefold()] = items
        i = block_end + 1

    return data


def _extract_see_also_from_block(block_lines: List[str]) -> list[str]:
    items: list[str] = []
    in_section = False

    for line in block_lines:
        stripped = line.strip()
        if stripped == "see_also:":
            in_section = True
            continue
        if not in_section:
            continue
        if _is_field_line(stripped):
            break
        if stripped and stripped not in items:
            items.append(stripped)

    return items


def _merge_see_also_into_block(block_lines: List[str], see_also_items: list[str] | None) -> List[str]:
    if not see_also_items:
        return [line.rstrip() for line in block_lines]

    inner = block_lines[1:-1]
    cleaned: list[str] = []
    existing_items: list[str] = []
    i = 0
    insert_at = None

    while i < len(inner):
        stripped = inner[i].strip()

        if stripped == "see_also:":
            i += 1
            while i < len(inner):
                candidate = inner[i].strip()
                if not candidate:
                    i += 1
                    continue
                if _is_field_line(candidate):
                    break
                if candidate not in existing_items:
                    existing_items.append(candidate)
                i += 1
            continue

        if _is_field_line(stripped) and insert_at is None and stripped.lower().startswith("tags:"):
            insert_at = len(cleaned)

        cleaned.append(inner[i].rstrip())
        i += 1

    combined_items: list[str] = []
    seen: set[str] = set()
    for item in [*existing_items, *see_also_items]:
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            combined_items.append(item)

    if insert_at is None:
        insert_at = len(cleaned)

    result = [BLOCK_START]
    result.extend(cleaned[:insert_at])
    result.append("see_also:")
    result.extend(combined_items)
    result.extend(cleaned[insert_at:])
    result.append(BLOCK_END)
    return result


def _is_field_line(stripped_line: str) -> bool:
    return bool(FIELD_LINE_RE.match(stripped_line))
