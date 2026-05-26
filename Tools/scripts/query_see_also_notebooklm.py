#!/usr/bin/env python3
"""
Generate Outputs/04_see_also.md by querying NotebookLM MCP with Outputs/03_word_list.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import URLError

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_NOTEBOOK_ID = "694ed21c-d4de-453e-8bec-60c4688127a0"
DEFAULT_NOTEBOOK_NAME = "Comprehensive German Language Learning and Vocabulary Guide"
DEFAULT_MCP_URL = "http://127.0.0.1:8010/mcp"
DEFAULT_REQUEST_TIMEOUT = 60.0
DEFAULT_QUERY_TIMEOUT = 180.0
DEFAULT_BATCH_SIZE = 20
DEFAULT_BATCH_MAX = 60
DEFAULT_BATCH_MIN = 1
DEFAULT_MAX_ATTEMPTS = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query NotebookLM MCP and generate Outputs/04_see_also.md"
    )
    parser.add_argument("--root", type=Path,
                        default=Path("."), help="Project root path")
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL,
                        help="NotebookLM MCP URL")
    parser.add_argument(
        "--notebook-id", default=DEFAULT_NOTEBOOK_ID, help="NotebookLM notebook id")
    parser.add_argument(
        "--notebook-name",
        default=DEFAULT_NOTEBOOK_NAME,
        help="NotebookLM notebook display name (for logging)",
    )
    parser.add_argument(
        "--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT, help="HTTP timeout seconds"
    )
    parser.add_argument(
        "--query-timeout", type=float, default=DEFAULT_QUERY_TIMEOUT, help="Notebook query timeout seconds"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Initial batch size for word list chunking.",
    )
    parser.add_argument(
        "--batch-max",
        type=int,
        default=DEFAULT_BATCH_MAX,
        help="Maximum adaptive batch size.",
    )
    parser.add_argument(
        "--batch-min",
        type=int,
        default=DEFAULT_BATCH_MIN,
        help="Minimum adaptive batch size.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help="Max attempts per batch before shrinking/splitting.",
    )
    return parser.parse_args()


def _read_sse_json(resp, *, timeout_s: float) -> str:
    """Read SSE stream until we see a JSON object (data: {...}) with id or error.

    NotebookLM MCP uses `text/event-stream` responses. Waiting for full `.read()`
    can hang if server keeps stream open. This reads line-by-line and returns as
    soon as a complete JSON payload is observed.
    """
    deadline = time.time() + timeout_s
    data_buf: list[str] = []

    while time.time() < deadline:
        raw = resp.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        if line.startswith("data:"):
            chunk = line[5:].strip()
            if chunk:
                data_buf.append(chunk)
                # Try parse newest chunk first (FastMCP sends whole JSON per data line).
                try:
                    obj = json.loads(chunk)
                    if isinstance(obj, dict) and ("id" in obj or "error" in obj or "result" in obj):
                        return chunk
                except json.JSONDecodeError:
                    pass
        # Some servers may send raw JSON without SSE prefix.
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    return line
            except json.JSONDecodeError:
                pass

    raise TimeoutError("SSE read timeout")


def post_json(url: str, payload: dict[str, object], headers: dict[str, str], timeout: float) -> tuple[dict[str, str], str]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        response_headers = {k.lower(): v for k, v in resp.headers.items()}
        ctype = response_headers.get("content-type", "")
        if "text/event-stream" in ctype:
            response_text = _read_sse_json(resp, timeout_s=timeout)
        else:
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
        line[5:].strip() for line in raw_text.splitlines() if line.startswith("data:") and line[5:].strip()
    ]
    for candidate in reversed(data_lines):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise RuntimeError("Unable to parse MCP response")


def call_tool(
    mcp_url: str,
    session_id: str,
    request_timeout: float,
    tool_name: str,
    arguments: dict[str, object],
    req_id: int = 2,
) -> dict[str, object]:
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": session_id,
    }
    _, raw_text = post_json(mcp_url, payload, headers, request_timeout)
    payload_dict = parse_mcp_response(raw_text)
    if "error" in payload_dict:
        raise RuntimeError(
            f"MCP {tool_name} failed: {json.dumps(payload_dict['error'], ensure_ascii=False)}"
        )
    result = payload_dict.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(
            f"Unexpected {tool_name} result: {json.dumps(payload_dict, ensure_ascii=False)[:1200]}"
        )
    return result


def refresh_auth_in_session(mcp_url: str, session_id: str, request_timeout: float) -> None:
    try:
        result = call_tool(
            mcp_url,
            session_id,
            request_timeout,
            "refresh_auth",
            {},
            req_id=98,
        )
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            status = structured.get("status")
            message = structured.get("message")
            if isinstance(status, str):
                print(f"[INFO] refresh_auth status: {status}")
            if isinstance(message, str) and message.strip():
                print(f"[INFO] refresh_auth message: {message}")
    except Exception as exc:
        print(f"[WARN] refresh_auth failed in-session: {exc}")


def _extract_json_from_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _collect_notebooks_from_obj(obj: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []

    if isinstance(obj, dict):
        nid = obj.get("id") or obj.get("notebook_id")
        name = obj.get("name") or obj.get("title")
        if isinstance(nid, str) and isinstance(name, str):
            found.append({"id": nid, "name": name})

        for value in obj.values():
            found.extend(_collect_notebooks_from_obj(value))
        return found

    if isinstance(obj, list):
        for item in obj:
            found.extend(_collect_notebooks_from_obj(item))

    return found


def list_notebooks(mcp_url: str, session_id: str, request_timeout: float) -> list[dict[str, str]]:
    result = call_tool(
        mcp_url,
        session_id,
        request_timeout,
        "notebook_list",
        {},
        req_id=99,
    )
    notebooks: list[dict[str, str]] = []
    notebooks.extend(_collect_notebooks_from_obj(result))

    if isinstance(result, dict):
        structured = result.get("structuredContent")
        notebooks.extend(_collect_notebooks_from_obj(structured))

        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parsed = _extract_json_from_text(text_value)
                    if parsed is not None:
                        notebooks.extend(_collect_notebooks_from_obj(parsed))

    deduped: dict[str, dict[str, str]] = {}
    for nb in notebooks:
        nb_id = nb.get("id")
        nb_name = nb.get("name")
        if isinstance(nb_id, str) and isinstance(nb_name, str):
            deduped[nb_id] = {"id": nb_id, "name": nb_name}

    return list(deduped.values())


def resolve_notebook_id(
    mcp_url: str,
    session_id: str,
    preferred_name: str,
    fallback_id: str,
    request_timeout: float,
) -> str:
    notebooks = list_notebooks(mcp_url, session_id, request_timeout)
    if not notebooks:
        print(
            "[WARN] notebook_list returned no notebooks after refresh_auth; "
            f"using provided notebook id: {fallback_id}"
        )
        return fallback_id

    lower_name = preferred_name.strip().lower()
    for nb in notebooks:
        if nb["name"].strip().lower() == lower_name:
            print(
                f"[INFO] Resolved notebook id from name: {nb['name']} -> {nb['id']}")
            return nb["id"]

    print(
        "[WARN] Notebook name not found in notebook_list. "
        f"Requested='{preferred_name}'. Using provided notebook id: {fallback_id}"
    )
    return fallback_id


def initialize_session(mcp_url: str, request_timeout: float) -> str:
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "nw3-query", "version": "1.0"},
        },
    }
    base_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    response_headers, _ = post_json(
        mcp_url, init_payload, base_headers, request_timeout)
    session_id = response_headers.get("mcp-session-id", "").strip()
    if not session_id:
        raise RuntimeError("Missing mcp-session-id from initialize")

    notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    notify_headers = {**base_headers, "Mcp-Session-Id": session_id}
    post_json(mcp_url, notify_payload, notify_headers, request_timeout)
    return session_id


def build_query(prompt_template: str, word_list_text: str) -> str:
    from gnw_pipeline.prompts import render_prompt

    return render_prompt(prompt_template, values={"word_list": word_list_text.strip()})


def query_notebook(
    mcp_url: str,
    session_id: str,
    notebook_id: str,
    query: str,
    request_timeout: float,
    query_timeout: float,
) -> str:
    result = call_tool(
        mcp_url,
        session_id,
        request_timeout,
        "notebook_query",
        {
            "notebook_id": notebook_id,
            "query": query,
            "timeout": query_timeout,
        },
        req_id=100,
    )

    structured = result.get("structuredContent", {})
    if isinstance(structured, dict):
        if structured.get("status") == "error":
            err = structured.get("error")
            if isinstance(err, str) and err.strip():
                raise RuntimeError(f"notebook_query returned error: {err}")
        answer = structured.get("answer")
        if isinstance(answer, str):
            return answer
        text_value = structured.get("text")
        if isinstance(text_value, str):
            return text_value

    output = result.get("output")
    if isinstance(output, str) and output.strip():
        return output

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
                if isinstance(nested, dict) and nested.get("status") == "error":
                    err = nested.get("error")
                    if isinstance(err, str) and err.strip():
                        raise RuntimeError(
                            f"notebook_query returned error: {err}")
                nested_answer = nested.get("answer")
                if isinstance(nested_answer, str):
                    return nested_answer
            except json.JSONDecodeError:
                if text_value.strip():
                    return text_value

    raise RuntimeError(
        "No text answer returned by notebook_query. "
        f"Response excerpt: {json.dumps(result, ensure_ascii=False)[:1200]}"
    )


def extract_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.findall(r"SSTART[\s\S]*?EEND", text)]


WORD_LINE_RE = re.compile(r"^(?:%word|%WORD|WORD|word)\s*:\s*(.+?)\s*$", re.MULTILINE)


def _block_word(block: str) -> str | None:
    m = WORD_LINE_RE.search(block)
    return m.group(1).strip() if m else None


def _words_from_word_list_md(text: str) -> list[str]:
    out: list[str] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if ln.startswith("- "):
            w = ln[2:].strip()
            if w:
                out.append(w)
    return out


def _write_blocks(out_path: Path, words_in_order: list[str], blocks_by_word: dict[str, str]) -> None:
    blocks = [blocks_by_word[w] for w in words_in_order if w in blocks_by_word]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(blocks).strip() + "\n", encoding="utf-8", newline="\n")


def _sleep_backoff(attempt: int) -> None:
    base = min(2 ** (attempt - 1), 8)
    jitter = 0.2 * (attempt % 3)
    time.sleep(base + jitter)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()

    words_file = root / "Outputs" / "03_word_list.md"
    prompt_file = root / "Prompt" / "nw3_notebooklm_query.md"
    out04 = root / "Outputs" / "04_see_also.md"

    if not words_file.exists():
        print(f"[ERROR] Missing file: {words_file}")
        return 1
    if not prompt_file.exists():
        print(f"[ERROR] Missing file: {prompt_file}")
        return 1

    word_list_text = words_file.read_text(encoding="utf-8")
    prompt_template = prompt_file.read_text(encoding="utf-8")
    words = _words_from_word_list_md(word_list_text)
    if not words:
        print(f"[ERROR] No words found in: {words_file}")
        return 1

    print(f"[INFO] Querying NotebookLM MCP at {args.mcp_url}")
    print(f"[INFO] Notebook: {args.notebook_name}")

    session_id = initialize_session(args.mcp_url, args.request_timeout)
    refresh_auth_in_session(args.mcp_url, session_id, args.request_timeout)
    notebook_id = resolve_notebook_id(
        args.mcp_url,
        session_id,
        args.notebook_name,
        args.notebook_id,
        args.request_timeout,
    )

    blocks_by_word: dict[str, str] = {}
    missing = list(words)
    batch_size = max(args.batch_min, min(args.batch_size, args.batch_max))

    print(f"[INFO] words={len(words)} batch_size={batch_size}")

    while missing:
        batch = missing[:batch_size]
        missing = missing[batch_size:]

        attempt = 1
        while True:
            query = build_query(
                prompt_template,
                "\n".join(f"- {w}" for w in batch),
            )
            try:
                http_timeout = max(args.request_timeout, args.query_timeout + 10.0)
                answer_text = query_notebook(
                    args.mcp_url,
                    session_id,
                    notebook_id,
                    query,
                    http_timeout,
                    args.query_timeout,
                )

                blocks = extract_blocks(answer_text)
                if not blocks:
                    raise RuntimeError("NotebookLM response did not contain SSTART...EEND blocks")

                got_words: set[str] = set()
                for b in blocks:
                    w = _block_word(b)
                    if not w:
                        continue
                    got_words.add(w.casefold())
                    if w not in blocks_by_word:
                        blocks_by_word[w] = b

                still_missing = [w for w in batch if w.casefold() not in got_words]
                if still_missing:
                    print(f"[WARN] batch missing {len(still_missing)}/{len(batch)}; requeue")
                    missing = still_missing + missing

                _write_blocks(out04, words, blocks_by_word)

                if not still_missing and batch_size < args.batch_max:
                    batch_size = min(batch_size * 2, args.batch_max)
                break
            except (TimeoutError, URLError, OSError, RuntimeError) as exc:
                print(f"[WARN] batch failed (attempt {attempt}/{args.max_attempts}): {exc}")
                if attempt >= args.max_attempts:
                    if batch_size > args.batch_min:
                        batch_size = max(args.batch_min, (batch_size + 1) // 2)
                        print(f"[INFO] shrinking batch_size -> {batch_size}")
                    missing = batch + missing
                    break
                _sleep_backoff(attempt)
                attempt += 1

    final_missing = [w for w in words if w not in blocks_by_word]
    if final_missing:
        print(f"[ERROR] Missing blocks for {len(final_missing)} words (first 20): {final_missing[:20]}")
        return 1

    print(f"[OK] Wrote {len(blocks_by_word)} blocks to: {out04}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
