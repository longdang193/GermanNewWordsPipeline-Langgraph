#!/usr/bin/env python3
"""
@meta
name: recover_missing_seealso
type: script
domain: german-vocabulary
responsibility:
    - Detect non-phrase entries missing see_also references
    - Detect entries with non-canonical see_also syntax
    - Query NotebookLM MCP for only affected entries
  - Rebuild downstream outputs and revalidate coverage
inputs:
  - Outputs/04_see_also.md
  - Outputs/02_words_fixed.md
  - Outputs/06_words_final.md
  - Outputs/06_words_final_fixed.md
outputs:
  - Outputs/04_see_also.md
  - Outputs/05_see_also_fixed.md
  - Outputs/06_words_final.md
  - Outputs/06_words_final_fixed.md
tags:
  - requirement-nw3
  - requirement-nw4
  - notebooklm-mcp
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib import request
from urllib.error import URLError

from mdproc.core import merge_see_also, preprocess_file1
from process_requirement4 import process_markdown_file
from mdproc.validation_core import CANONICAL_SEE_ALSO_RE, validate_single_word_requires_see_also

DEFAULT_NOTEBOOK_ID = "694ed21c-d4de-453e-8bec-60c4688127a0"
DEFAULT_MCP_URL = "http://127.0.0.1:8010/mcp"
DEFAULT_MAX_ROUNDS = 3
DEFAULT_REQUEST_TIMEOUT = 60.0
DEFAULT_QUERY_TIMEOUT = 180.0

MISSING_WORD_RE = re.compile(
    r"non-phrase block '(.+?)' must contain a non-empty see_also field"
)


@dataclass(frozen=True)
class OutputPaths:
    out02: Path
    out04: Path
    out05: Path
    out06: Path
    out06_fixed: Path


class RecoveryError(RuntimeError):
    """Raised when the recovery flow cannot continue safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recover missing or non-canonical see_also entries via NotebookLM MCP and rebuild outputs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root containing the Outputs directory (default: current directory).",
    )
    parser.add_argument(
        "--mcp-url",
        default=DEFAULT_MCP_URL,
        help="NotebookLM MCP HTTP endpoint.",
    )
    parser.add_argument(
        "--notebook-id",
        default=DEFAULT_NOTEBOOK_ID,
        help="NotebookLM notebook id to query.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=DEFAULT_MAX_ROUNDS,
        help="Maximum recovery rounds to attempt.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT,
        help="HTTP timeout in seconds for MCP calls.",
    )
    parser.add_argument(
        "--query-timeout",
        type=float,
        default=DEFAULT_QUERY_TIMEOUT,
        help="Notebook query timeout in seconds passed to notebook_query.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report missing words and planned actions.",
    )
    return parser.parse_args()


def build_paths(root: Path) -> OutputPaths:
    output_dir = root / "Outputs"
    return OutputPaths(
        out02=output_dir / "02_words_fixed.md",
        out04=output_dir / "04_see_also.md",
        out05=output_dir / "05_see_also_fixed.md",
        out06=output_dir / "06_words_final.md",
        out06_fixed=output_dir / "06_words_final_fixed.md",
    )


def require_files(paths: OutputPaths) -> None:
    required = [paths.out02, paths.out04, paths.out06]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        missing_text = "\n".join(f"- {item}" for item in missing)
        raise RecoveryError(f"Required files are missing:\n{missing_text}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_fixed_output(paths: OutputPaths) -> None:
    if paths.out06_fixed.exists():
        return
    process_markdown_file(paths.out06, paths.out06_fixed)


def extract_missing_words(final_fixed_text: str) -> list[str]:
    issues = validate_single_word_requires_see_also(
        final_fixed_text.splitlines())
    ordered_words: list[str] = []
    seen: set[str] = set()

    for issue in issues:
        match = MISSING_WORD_RE.search(issue)
        if not match:
            continue
        word = match.group(1).strip()
        key = word.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered_words.append(word)

    return ordered_words


def extract_words_with_noncanonical_see_also(final_fixed_text: str) -> list[str]:
    """Return words whose see_also section contains non-canonical entries."""
    lines = final_fixed_text.splitlines()
    i = 0
    ordered_words: list[str] = []
    seen: set[str] = set()

    while i < len(lines):
        if lines[i].strip() != "SSTART":
            i += 1
            continue

        j = i + 1
        while j < len(lines) and lines[j].strip() != "EEND":
            j += 1

        if j >= len(lines):
            break

        block = lines[i: j + 1]
        word = ""
        in_see_also = False
        has_noncanonical = False

        for raw in block:
            stripped = raw.strip()
            if stripped.startswith("word:"):
                word = stripped.split(":", 1)[1].strip()
                continue

            if stripped == "see_also:":
                in_see_also = True
                continue

            if in_see_also:
                if not stripped:
                    continue

                # Field header means see_also section has ended.
                if ":" in stripped and not stripped.startswith("[") and not stripped.startswith("der ") and not stripped.startswith("die ") and not stripped.startswith("das "):
                    in_see_also = False
                    continue

                if "|nid" in stripped and not CANONICAL_SEE_ALSO_RE.match(stripped):
                    has_noncanonical = True

        if has_noncanonical and word:
            key = word.casefold()
            if key not in seen:
                seen.add(key)
                ordered_words.append(word)

        i = j + 1

    return ordered_words


def merge_targets(primary: Iterable[str], secondary: Iterable[str]) -> list[str]:
    """Merge ordered word collections with case-insensitive uniqueness."""
    merged: list[str] = []
    seen: set[str] = set()

    for collection in (primary, secondary):
        for word in collection:
            key = word.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(word)

    return merged


def build_query(missing_words: Iterable[str]) -> str:
    word_lines = "\n".join(missing_words)
    return (
        "Task: Generate ONLY see_also blocks for the listed words that need repair.\n"
        "Output must contain only SSTART...EEND blocks, no prose, no markdown.\n"
        "Format per block:\n"
        "SSTART\n"
        "%VOCAB (German) ver 3\n"
        "word: <exact word from list>\n"
        "see_also:\n"
        "<entry format: [term|nid123...] = short English meaning>\n"
        "Tags: <same POS tag style as existing file>\n"
        "EEND\n\n"
        "Rules:\n"
        "- Every see_also line must follow: [term|nid123...] = short English meaning\n"
        "- For noun terms, article is mandatory: der/die/das [Noun|nid...]\n"
        "- For non-nouns, no article.\n"
        "- Provide 3-5 high-quality relevant entries per word when possible.\n"
        "- Keep exact word text as provided (including punctuation/parentheses).\n"
        "- Return blocks only for these words:\n"
        f"{word_lines}\n"
    )


def post_mcp(
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    request_timeout: float,
) -> tuple[dict[str, str], str]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=request_timeout) as resp:
        response_headers = {
            key.lower(): value for key, value in resp.headers.items()
        }
        response_text = resp.read().decode("utf-8", errors="replace")
    return response_headers, response_text


def parse_mcp_response(raw_text: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    data_lines = [
        line[5:].strip()
        for line in raw_text.splitlines()
        if line.startswith("data:") and line[5:].strip()
    ]
    for candidate in reversed(data_lines):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise RecoveryError("Unable to parse MCP response payload.")


def initialize_session(mcp_url: str, request_timeout: float) -> str:
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "recovery-script", "version": "1.0"},
        },
    }
    base_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    response_headers, _ = post_mcp(
        mcp_url, init_payload, base_headers, request_timeout
    )
    session_id = response_headers.get("mcp-session-id", "").strip()
    if not session_id:
        raise RecoveryError("MCP initialize did not return mcp-session-id.")

    notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    notify_headers = {
        **base_headers,
        "Mcp-Session-Id": session_id,
    }
    post_mcp(mcp_url, notify_payload, notify_headers, request_timeout)
    return session_id


def query_notebook(
    mcp_url: str,
    notebook_id: str,
    query: str,
    session_id: str,
    request_timeout: float,
    query_timeout: float,
) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "notebook_query",
            "arguments": {
                "notebook_id": notebook_id,
                "query": query,
                "timeout": query_timeout,
            },
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": session_id,
    }
    _, raw_text = post_mcp(mcp_url, payload, headers, request_timeout)
    response_payload = parse_mcp_response(raw_text)

    result = response_payload.get("result", {})
    if not isinstance(result, dict):
        raise RecoveryError("Unexpected MCP response: missing result object.")

    structured = result.get("structuredContent", {})
    if isinstance(structured, dict):
        answer = structured.get("answer")
        if isinstance(answer, str) and "SSTART" in answer:
            return answer

    content = result.get("content", [])
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            text_value = item.get("text")
            if not isinstance(text_value, str):
                continue
            try:
                nested = json.loads(text_value)
                nested_answer = nested.get("answer")
                if isinstance(nested_answer, str) and "SSTART" in nested_answer:
                    return nested_answer
            except json.JSONDecodeError:
                if "SSTART" in text_value:
                    return text_value

    raise RecoveryError("Notebook query did not return SSTART...EEND blocks.")


def extract_blocks(answer_text: str) -> list[str]:
    blocks = re.findall(r"SSTART[\s\S]*?EEND", answer_text)
    return [block.strip() for block in blocks]


def parse_block_word(block: str) -> str:
    match = re.search(r"(?m)^word:\s*(.+)$", block)
    if not match:
        raise RecoveryError("Encountered block without a word field.")
    return match.group(1).strip()


def append_new_blocks(file_path: Path, candidate_blocks: Iterable[str]) -> int:
    existing = read_text(file_path)
    existing_words = {
        match.group(1).strip().casefold()
        for match in re.finditer(r"(?m)^word:\s*(.+)$", existing)
    }

    new_blocks: list[str] = []
    for block in candidate_blocks:
        word = parse_block_word(block)
        key = word.casefold()
        if key in existing_words:
            continue
        existing_words.add(key)
        new_blocks.append(block)

    if not new_blocks:
        return 0

    append_text = "\n" + "\n\n".join(new_blocks) + "\n"
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(append_text)

    return len(new_blocks)


def upsert_blocks(file_path: Path, candidate_blocks: Iterable[str]) -> tuple[int, int]:
    """Replace existing blocks by word (case-insensitive) and append new ones."""
    existing_text = read_text(file_path)
    existing_blocks = extract_blocks(existing_text)
    normalized_blocks = [block.strip() for block in existing_blocks]

    index_by_word: dict[str, int] = {}
    for idx, block in enumerate(normalized_blocks):
        try:
            word = parse_block_word(block)
        except RecoveryError:
            continue
        index_by_word[word.casefold()] = idx

    replaced = 0
    appended = 0
    for block in candidate_blocks:
        word = parse_block_word(block)
        key = word.casefold()
        if key in index_by_word:
            normalized_blocks[index_by_word[key]] = block.strip()
            replaced += 1
            continue

        index_by_word[key] = len(normalized_blocks)
        normalized_blocks.append(block.strip())
        appended += 1

    if not normalized_blocks:
        return replaced, appended

    write_text(file_path, "\n\n".join(normalized_blocks) + "\n")
    return replaced, appended


def rebuild_pipeline_outputs(paths: OutputPaths) -> None:
    out04_text = read_text(paths.out04)
    out05_text = preprocess_file1(out04_text)
    write_text(paths.out05, out05_text)

    out02_text = read_text(paths.out02)
    out06_text = merge_see_also(out05_text, out02_text)
    write_text(paths.out06, out06_text)

    process_markdown_file(paths.out06, paths.out06_fixed)


def run_recovery(args: argparse.Namespace, paths: OutputPaths) -> int:
    ensure_fixed_output(paths)

    for round_idx in range(1, args.max_rounds + 1):
        final_fixed_text = read_text(paths.out06_fixed)
        missing_words = extract_missing_words(final_fixed_text)
        noncanonical_words = extract_words_with_noncanonical_see_also(
            final_fixed_text)
        target_words = merge_targets(missing_words, noncanonical_words)

        if not target_words:
            print("[OK] No missing or non-canonical see_also entries detected.")
            return 0

        print(
            f"🔄 Round {round_idx}: found {len(target_words)} words needing see_also repair."
        )
        if missing_words:
            print(f"  Missing see_also words: {len(missing_words)}")
        if noncanonical_words:
            print(f"  Non-canonical see_also words: {len(noncanonical_words)}")

        for word in target_words:
            print(f"  - {word}")

        if args.dry_run:
            return 0

        query = build_query(target_words)
        session_id = initialize_session(args.mcp_url, args.request_timeout)
        answer_text = query_notebook(
            mcp_url=args.mcp_url,
            notebook_id=args.notebook_id,
            query=query,
            session_id=session_id,
            request_timeout=args.request_timeout,
            query_timeout=args.query_timeout,
        )

        blocks = extract_blocks(answer_text)
        if not blocks:
            raise RecoveryError("Notebook query returned zero blocks.")

        replaced, appended = upsert_blocks(paths.out04, blocks)
        print(
            f"📝 Updated {paths.out04}: replaced {replaced} blocks, appended {appended} blocks."
        )

        if replaced == 0 and appended == 0:
            raise RecoveryError(
                "No blocks were updated; cannot make progress on see_also recovery."
            )

        rebuild_pipeline_outputs(paths)

    final_missing = extract_missing_words(read_text(paths.out06_fixed))
    final_noncanonical = extract_words_with_noncanonical_see_also(
        read_text(paths.out06_fixed))
    if final_missing or final_noncanonical:
        raise RecoveryError(
            f"Missing or non-canonical see_also still present after {args.max_rounds} rounds."
        )

    return 0


def main() -> int:
    args = parse_args()

    if args.max_rounds < 1:
        print("[ERROR] --max-rounds must be >= 1")
        return 1

    project_root = args.root.resolve()
    paths = build_paths(project_root)

    try:
        require_files(paths)
        return run_recovery(args, paths)
    except (RecoveryError, URLError, OSError, ValueError, json.JSONDecodeError) as err:
        print(f"[ERROR] Recovery failed: {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
