#!/usr/bin/env python3
"""
Requirement NW3 helper: generate Outputs/04_see_also.md via NotebookLM MCP.

Design goals:
- Resumable: writes incrementally so we can stop/re-run without losing work.
- Robust: retries on timeouts / malformed blocks by restarting MCP process.

This uses the local NotebookLM MCP stdio server binary: notebooklm-mcp.
Auth must already be cached (run `notebooklm-mcp-auth` once if needed).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from notebooklm_errors import classify_notebooklm_error, should_abort_notebooklm_bootstrap


ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
WORDLIST_PATH = ROOT / "Outputs" / "03_word_list.md"
OUT_PATH = ROOT / "Outputs" / "04_see_also.md"

TARGET_NOTEBOOK_TITLE = "Comprehensive German Language Learning and Vocabulary Guide"


BLOCK_RE = re.compile(r"SSTART\s*\n[\s\S]*?\nEEND")
WORD_LINE_RE = re.compile(r"^(?:%word|WORD|word):\s*(.+?)\s*$", re.MULTILINE)
NID_LINE_RE = re.compile(r"nid\d+")
NOT_FOUND_RE = re.compile(r"\bnot found\b", re.IGNORECASE)


def count_see_also_entries(block: str) -> int:
    lines = block.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    in_see_also = False
    count = 0
    for raw in lines:
        s = raw.strip()
        if s == "see_also:":
            in_see_also = True
            continue
        if not in_see_also:
            continue
        if s == "EEND":
            break
        if s and re.match(r"^[A-Za-z_][A-Za-z0-9_]*\\s*:", s):
            break
        if s:
            count += 1
    return count


def read_words() -> list[str]:
    lines = WORDLIST_PATH.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for ln in lines:
        ln = ln.strip()
        if ln.startswith("- "):
            out.append(ln[2:].strip())
    return out


def split_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Handle slash-compressed fallback: SSTART/word/.../EEND
    if "SSTART/" in text and "/EEND" in text:
        rebuilt: list[str] = []
        for m in re.finditer(r"SSTART/([^/\n]+)/([\s\S]*?)/EEND", text):
            word = m.group(1).strip()
            body = m.group(2)
            lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
            rebuilt.append(
                "SSTART\n%word: " + word + "\nsee_also:\n" + "\n".join(lines) + "\nEEND"
            )
        if rebuilt:
            text = "\n\n".join(rebuilt)
    return [b.strip() for b in BLOCK_RE.findall(text)]


def get_block_word(block: str) -> str | None:
    m = WORD_LINE_RE.search(block)
    return m.group(1).strip() if m else None


def block_ok(block: str) -> bool:
    if NOT_FOUND_RE.search(block):
        return False
    if "see_also:" not in block:
        return False
    if not NID_LINE_RE.search(block):
        return False
    from gnw_pipeline.runtime_config import load_runtime_config

    cfg = load_runtime_config(root=ROOT).nw3
    entry_count = count_see_also_entries(block)
    if entry_count < cfg.min_see_also_entries or entry_count > cfg.max_see_also_entries:
        return False
    return True


JsonObject = dict[str, Any]


@dataclass
class McpSession:
    proc: subprocess.Popen[str]
    next_id: int
    notebook_id: str


def _send(proc: subprocess.Popen[str], msg: JsonObject) -> None:
    proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")  # type: ignore[union-attr]
    proc.stdin.flush()  # type: ignore[union-attr]


def _recv(proc: subprocess.Popen[str], timeout_s: float) -> JsonObject:
    start = time.time()
    while time.time() - start < timeout_s:
        line = proc.stdout.readline()  # type: ignore[union-attr]
        if not line:
            continue
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            return cast(JsonObject, payload)
    raise TimeoutError("MCP response timeout")


def _tool_call(
    session: McpSession,
    name: str,
    arguments: JsonObject,
    timeout_s: float,
) -> JsonObject:
    call_id = session.next_id
    session.next_id += 1
    _send(
        session.proc,
        {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    return _recv(session.proc, timeout_s)


def _tool_answer_text(resp: JsonObject) -> str:
    res = resp.get("result", {})
    sc = res.get("structuredContent")
    if isinstance(sc, dict) and "answer" in sc:
        return sc.get("answer", "") or ""
    # fallback: content[0].text could contain JSON string
    text = "".join(
        part.get("text", "") for part in res.get("content", []) if part.get("type") == "text"
    )
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "answer" in obj:
            return obj.get("answer", "") or ""
    except Exception:
        pass
    return text


def start_session() -> McpSession:
    proc = subprocess.Popen(
        ["notebooklm-mcp", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "clientInfo": {"name": "german_new_words", "version": "0.1"},
            },
        },
    )
    _recv(proc, 20.0)
    _send(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})

    session = McpSession(proc=proc, next_id=2, notebook_id="")
    _tool_call(session, "refresh_auth", {}, 30.0)

    resp = _tool_call(session, "notebook_list", {"max_results": 200}, 60.0)
    text = "".join(
        part.get("text", "") for part in resp.get("result", {}).get("content", []) if part.get("type") == "text"
    )
    obj = json.loads(text)
    if obj.get("status") != "success":
        raise RuntimeError(f"notebook_list failed: {obj}")
    notebooks = obj.get("notebooks", [])
    match = [n for n in notebooks if (n.get("title") or "").strip() == TARGET_NOTEBOOK_TITLE]
    if not match:
        raise RuntimeError("Target notebook not found in notebook_list")
    session.notebook_id = match[0]["id"]
    return session


def stop_session(session: McpSession) -> None:
    try:
        session.proc.terminate()
    except Exception:
        pass


def build_query(words: list[str]) -> str:
    from gnw_pipeline.prompts import load_prompt, render_prompt

    list_text = "\n".join(f"- {w}" for w in words)
    template = load_prompt("nw3_notebooklm_query", root=ROOT)
    return render_prompt(template, values={"word_list": list_text})


def load_existing_blocks() -> dict[str, str]:
    if not OUT_PATH.exists():
        return {}
    text = OUT_PATH.read_text(encoding="utf-8", errors="replace")
    out: dict[str, str] = {}
    for b in split_blocks(text):
        w = get_block_word(b)
        if w and w not in out and block_ok(b):
            out[w] = b
    return out


def main() -> int:
    if not WORDLIST_PATH.exists():
        raise SystemExit(f"Missing word list: {WORDLIST_PATH}")

    words = read_words()
    existing = load_existing_blocks()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    done_count = sum(1 for w in words if w in existing)
    print(f"[info] words={len(words)} already_done={done_count}")

    blocks_by_word = dict(existing)

    if not words:
        OUT_PATH.write_text("", encoding="utf-8")
        print(f"[info] wrote={OUT_PATH} blocks=0 missing=0")
        return 0

    from gnw_pipeline.runtime_config import load_runtime_config

    cfg = load_runtime_config(root=ROOT).nw3
    chunk_size = cfg.chunk_size
    max_passes = cfg.max_passes  # retry passes for stubborn words
    max_session_start_failures = 3
    session_start_failures = 0

    for pass_num in range(1, max_passes + 1):
        missing = [w for w in words if w not in blocks_by_word]
        if not missing:
            break

        print(f"[info] pass={pass_num} missing={len(missing)}")

        idx = 0
        while idx < len(missing):
            chunk = missing[idx : idx + chunk_size]
            idx += chunk_size

            session: McpSession | None = None
            try:
                session = start_session()
                session_start_failures = 0
                query = build_query(chunk)
                resp = _tool_call(
                    session,
                    "notebook_query",
                    {"notebook_id": session.notebook_id, "query": query, "timeout": 420},
                    timeout_s=600.0,
                )
                ans = _tool_answer_text(resp)
                new_blocks = split_blocks(ans)
                for b in new_blocks:
                    w = get_block_word(b)
                    if not w:
                        continue
                    if w in blocks_by_word:
                        continue
                    if not block_ok(b):
                        continue
                    blocks_by_word[w] = b
            except TimeoutError:
                # Shrink chunk size on timeouts.
                if chunk_size > 1:
                    chunk_size = 1
                print("[warn] timeout; reducing chunk_size and retrying later")
            except Exception as e:
                error_text = str(e)
                if session is None:
                    session_start_failures += 1
                    error_kind = classify_notebooklm_error(error_text)
                    print(
                        f"[warn] session bootstrap failed ({error_kind}) "
                        f"attempt={session_start_failures}: {e}"
                    )
                    if should_abort_notebooklm_bootstrap(
                        error_text,
                        consecutive_failures=session_start_failures,
                        max_failures=max_session_start_failures,
                    ):
                        if error_kind == "auth":
                            print(
                                "[error] NotebookLM auth/session is invalid. "
                                "Run notebooklm-mcp-auth and rerun NW3."
                            )
                        else:
                            print(
                                "[error] NotebookLM session bootstrap failed repeatedly. "
                                "Check network/auth, then rerun NW3."
                            )
                        return 1
                else:
                    print(f"[warn] query failed: {e}")
            finally:
                if session is not None:
                    stop_session(session)

            # Incremental write after each chunk
            out_blocks = [blocks_by_word[w] for w in words if w in blocks_by_word]
            OUT_PATH.write_text("\n\n".join(out_blocks).strip() + "\n", encoding="utf-8")

    missing_final = [w for w in words if w not in blocks_by_word]
    print(f"[info] wrote={OUT_PATH} blocks={len(blocks_by_word)} missing={len(missing_final)}")
    if missing_final:
        print("[error] missing words (first 20): " + "; ".join(missing_final[:20]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
