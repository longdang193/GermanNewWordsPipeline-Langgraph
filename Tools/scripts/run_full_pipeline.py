#!/usr/bin/env python3
"""
Run NW1 -> NW4 automatically with minimal user intervention.

Behavior:
- Runs Requirement NW1 and NW2 scripts/commands.
- Ensures NotebookLM MCP server is reachable for NW3.
- Tries to query real see_also data via NotebookLM MCP.
- If MCP auth is expired, attempts automatic re-auth once.
- Only asks user action when interactive auth is required.
- Runs NW4 processing and validations.
"""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import request
from urllib.error import URLError
from datetime import datetime, timezone
from typing import Any, TextIO

from notebooklm_errors import classify_notebooklm_error


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "Tools" / "scripts"
MCP_HEALTH_URL = "http://127.0.0.1:8010/health"
MCP_SERVER_CMD = ["notebooklm-mcp", "--transport", "http", "--port", "8010"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8", errors="replace"))
    return h.hexdigest()


def compute_run_id() -> str:
    parts: list[str] = []
    for rel in (
        "Inputs/Word List (DE).md",
        "Prompt/nw1_enrich_system.txt",
        "Prompt/nw1_enrich_instructions.md",
        "Prompt/nw1_qa_system.txt",
        "Prompt/nw1_qa_instructions.md",
        "Prompt/nw3_notebooklm_query.md",
        "Requirement/Requirement NW1 - German new words prompt.md",
        "Requirement/Requirement NW2 - Validate and Normalize Vocabulary Fields.md",
        "Requirement/Requirement NW3 - Merge see_also Cross-References into Final Vocabulary Database.md",
        "Requirement/Requirement NW4 - Validate and Normalize see_also Anki References.md",
        "configs/runtime.toml",
    ):
        p = ROOT / rel
        if p.exists():
            parts.append(f"## {rel}\n{p.read_text(encoding='utf-8', errors='replace')}\n")
        else:
            parts.append(f"## {rel}\n<MISSING>\n")
    return _sha256_text("\n".join(parts))

def compute_prompt_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in (
        "Prompt/nw1_enrich_system.txt",
        "Prompt/nw1_enrich_instructions.md",
        "Prompt/nw1_qa_system.txt",
        "Prompt/nw1_qa_instructions.md",
        "Prompt/nw3_notebooklm_query.md",
        "configs/runtime.toml",
    ):
        p = ROOT / rel
        if p.exists():
            out[rel] = _sha256_text(p.read_text(encoding="utf-8", errors="replace"))
        else:
            out[rel] = "<MISSING>"
    return out

def clear_proxy_env() -> None:
    # NotebookLM MCP can fail/hang when proxy env points to dead local proxy (common in NW3 docs).
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if os.environ.get(k):
            os.environ[k] = ""


def run_cmd(
    cmd: list[str],
    desc: str,
    *,
    log_fp: TextIO,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    print(f"\n[STEP] {desc}")
    print(f"[CMD] {' '.join(cmd)}")
    log_fp.write(f"\n[{_utc_now_iso()}] [STEP] {desc}\n")
    log_fp.write(f"[{_utc_now_iso()}] [CMD] {' '.join(cmd)}\n")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
        log_fp.write(proc.stdout.rstrip() + "\n")
    if proc.stderr:
        print(proc.stderr.rstrip())
        log_fp.write(proc.stderr.rstrip() + "\n")
    print(f"[EXIT] {proc.returncode}")
    log_fp.write(f"[{_utc_now_iso()}] [EXIT] {proc.returncode}\n")
    log_fp.flush()
    return proc


def is_mcp_healthy() -> bool:
    try:
        with request.urlopen(MCP_HEALTH_URL, timeout=3) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
        parsed: Any = json.loads(payload)
        return isinstance(parsed, dict) and parsed.get("status") == "healthy"
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return False


def ensure_mcp_server() -> None:
    if is_mcp_healthy():
        print("[INFO] NotebookLM MCP server is already healthy.")
        return

    print("[INFO] Starting NotebookLM MCP server...")
    subprocess.Popen(MCP_SERVER_CMD, cwd=str(ROOT))

    for _ in range(20):
        if is_mcp_healthy():
            print("[INFO] NotebookLM MCP server is healthy.")
            return
        time.sleep(1)

    raise RuntimeError(
        "NotebookLM MCP server failed to become healthy on port 8010.")


def restart_mcp_server() -> None:
    print("[INFO] Restarting NotebookLM MCP server to refresh auth/session state...")
    subprocess.run(
        ["taskkill", "/F", "/IM", "notebooklm-mcp.exe"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    time.sleep(1)
    ensure_mcp_server()


def is_transient_notebook_error(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "incomplete chunked read",
            "peer closed connection",
            "incomplete message body",
            "connection reset by peer",
            "remote end closed connection",
        )
    )


def run_notebooklm_auth(*, cwd: Path) -> int:
    env = os.environ.copy()
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if env.get(k):
            env[k] = ""
    print("[STEP] NotebookLM MCP auth (interactive if needed)")
    proc = subprocess.run(["notebooklm-mcp-auth"], cwd=str(cwd), env=env)
    return proc.returncode

def count_word_list_entries(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip().startswith("- "):
            count += 1
    return count

def run_pipeline() -> int:
    logs_dir = ROOT / "Outputs" / "logs"
    reports_dir = ROOT / "Outputs" / "reports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    run_id = compute_run_id()
    log_path = logs_dir / "run_latest.log"

    with log_path.open("w", encoding="utf-8", newline="\n") as log_fp:
        log_fp.write(f"[{_utc_now_iso()}] run_id={run_id}\n")
        log_fp.flush()

        clear_proxy_env()
        log_fp.write(f"[{_utc_now_iso()}] proxy_env_cleared=true\n")
        log_fp.flush()

        outputs_word_file = ROOT / "Outputs" / "01_words.md"
        if outputs_word_file.exists():
            outputs_word_file.unlink()
        legacy_word_file = ROOT / "01_words.md"
        if legacy_word_file.exists():
            legacy_word_file.unlink()

        # NW1
        run_cmd(
            [sys.executable, str(SCRIPTS / "process_requirement1.py")],
            "NW1: Generate Outputs/01_words.md",
            log_fp=log_fp,
        )
        v1 = run_cmd(
            [sys.executable, str(SCRIPTS / "validate_word_list.py")],
            "NW1: Validate Outputs/01_words.md",
            log_fp=log_fp,
        )
        if v1.returncode != 0:
            print("\n[STOP] NW1 validation failed. Fix NW1 generation quality first.")
            return 1

        if (ROOT / "Outputs" / "01_words.md").exists() and (ROOT / "Tools" / "scripts" / "nw1_qa_review.py").exists():
            if (os.environ.get("GNW_ENABLE_NW1_QA", "0") == "1"):
                cmd = [sys.executable, str(SCRIPTS / "nw1_qa_review.py"), "--root", "."]
                if os.environ.get("GNW_ENABLE_NW1_LLM_QA", "0") == "1":
                    cmd.append("--llm")
                run_cmd(
                    cmd,
                    "NW1: QA review (optional)",
                    log_fp=log_fp,
                )

        # NW2
        n2a = run_cmd(
            ["py", "-m", "mdproc", "process", "Outputs/01_words.md", "--output", "Outputs/02_words_fixed.md"],
            "NW2: Normalize words",
            log_fp=log_fp,
        )
        if n2a.returncode != 0:
            return 1

        n2b = run_cmd(
            ["py", "-m", "mdproc", "words", "Outputs/02_words_fixed.md", "--output", "Outputs/03_word_list.md"],
            "NW2: Extract word list",
            log_fp=log_fp,
        )
        if n2b.returncode != 0:
            return 1

        word_list_count = count_word_list_entries(ROOT / "Outputs" / "03_word_list.md")
        if word_list_count == 0:
            (ROOT / "Outputs" / "04_see_also.md").write_text("", encoding="utf-8", newline="\n")
            (ROOT / "Outputs" / "05_see_also_fixed.md").write_text("", encoding="utf-8", newline="\n")
            (ROOT / "Outputs" / "06_words_final.md").write_text("", encoding="utf-8", newline="\n")
            (ROOT / "Outputs" / "06_words_final_fixed.md").write_text("", encoding="utf-8", newline="\n")

            run_latest = reports_dir / "run_latest.json"
            runs_jsonl = reports_dir / "runs.jsonl"
            summary = {
                "timestamp_utc": _utc_now_iso(),
                "run_id": run_id,
                "status": "ok_empty",
                "note": "No resolved NW1 entries; pipeline short-circuited after NW2.",
                "outputs": {
                    "final_markdown": str(ROOT / "Outputs" / "06_words_final_fixed.md"),
                    "log": str(log_path),
                },
            }
            run_latest.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            with runs_jsonl.open("a", encoding="utf-8", newline="\n") as fp:
                fp.write(json.dumps(summary, ensure_ascii=False) + "\n")

            print("\n[OK] Pipeline completed (empty run).")
            return 0

        # NW3
        # Use stdio-based NotebookLM MCP query helper (more robust than HTTP SSE in practice).
        q = run_cmd(
            [sys.executable, str(SCRIPTS / "generate_requirement3_notebooklm.py")],
            "NW3: Query NotebookLM (stdio) and generate Outputs/04_see_also.md",
            log_fp=log_fp,
        )

        if q.returncode != 0:
            combined = (q.stdout or "") + "\n" + (q.stderr or "")
            error_kind = classify_notebooklm_error(combined)
            if error_kind == "auth":
                print("[INFO] NotebookLM auth/session invalid. Attempting re-auth once...")
                if run_notebooklm_auth(cwd=ROOT) != 0:
                    return 1
                q_retry = run_cmd(
                    [sys.executable, str(SCRIPTS / "generate_requirement3_notebooklm.py")],
                    "NW3: Query NotebookLM (retry after auth)",
                    log_fp=log_fp,
                )
                if q_retry.returncode != 0:
                    retry_kind = classify_notebooklm_error(
                        (q_retry.stdout or "") + "\n" + (q_retry.stderr or "")
                    )
                    if retry_kind == "auth":
                        print("[STOP] NotebookLM auth/session still invalid after re-auth.")
                    elif retry_kind == "network":
                        print("[STOP] NotebookLM retry failed due network/session bootstrap issues.")
                    return 1
            else:
                # stdio helper prints actionable errors itself; keep runner simple.
                return 1

        n3a = run_cmd(
            ["py", "-m", "mdproc", "preprocess", "Outputs/04_see_also.md", "--output", "Outputs/05_see_also_fixed.md"],
            "NW3: Preprocess see_also",
            log_fp=log_fp,
        )
        if n3a.returncode != 0:
            return 1

        n3b = run_cmd(
            [
                "py",
                "-m",
                "mdproc",
                "merge-see-also",
                "Outputs/05_see_also_fixed.md",
                "Outputs/02_words_fixed.md",
                "--output",
                "Outputs/06_words_final.md",
            ],
            "NW3: Merge see_also",
            log_fp=log_fp,
        )
        if n3b.returncode != 0:
            return 1

        # NW4
        n4a = run_cmd(
            [sys.executable, str(SCRIPTS / "process_requirement4.py")],
            "NW4: Normalize see_also references",
            log_fp=log_fp,
        )
        if n4a.returncode != 0:
            return 1

        n4c = run_cmd(
            [sys.executable, str(SCRIPTS / "validate_requirement4.py")],
            "NW4: Deep validation (authoritative)",
            log_fp=log_fp,
        )
        if n4c.returncode != 0:
            recover_script = SCRIPTS / "recover_missing_seealso.py"
            if recover_script.exists():
                print("[INFO] NW4 validation failed. Attempting automatic recovery via recover_missing_seealso.py ...")
                r1 = run_cmd(
                    [sys.executable, str(recover_script)],
                    "NW4: Recovery (recover_missing_seealso.py)",
                    log_fp=log_fp,
                )
                if r1.returncode != 0:
                    return 1

                # Re-run processing + validation after recovery.
                n4a_retry = run_cmd(
                    [sys.executable, str(SCRIPTS / "process_requirement4.py")],
                    "NW4: Normalize see_also references (post-recovery)",
                    log_fp=log_fp,
                )
                if n4a_retry.returncode != 0:
                    return 1
                n4c_retry = run_cmd(
                    [sys.executable, str(SCRIPTS / "validate_requirement4.py")],
                    "NW4: Deep validation (post-recovery)",
                    log_fp=log_fp,
                )
                if n4c_retry.returncode != 0:
                    return 1
            else:
                return 1

        n4d = run_cmd(
            [sys.executable, str(SCRIPTS / "validate_see_also_authenticity.py"), "--input", "Outputs/04_see_also.md"],
            "NW3/NW4: Authenticity validation",
            log_fp=log_fp,
        )
        if n4d.returncode != 0:
            print("\n[WARN] Authenticity check flagged issues. Please verify NotebookLM source quality.")

        run_latest = reports_dir / "run_latest.json"
        runs_jsonl = reports_dir / "runs.jsonl"

        summary = {
            "timestamp_utc": _utc_now_iso(),
            "run_id": run_id,
            "hashes": compute_prompt_hashes(),
            "outputs": {
                "final_markdown": str(ROOT / "Outputs" / "06_words_final_fixed.md"),
                "log": str(log_path),
            },
            "status": "ok",
        }
        run_latest.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        existing_run_ids: set[str] = set()
        if runs_jsonl.exists():
            for ln in runs_jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    obj = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                rid = obj.get("run_id")
                if isinstance(rid, str):
                    existing_run_ids.add(rid)

        if run_id not in existing_run_ids:
            with runs_jsonl.open("a", encoding="utf-8", newline="\n") as fp:
                fp.write(json.dumps(summary, ensure_ascii=False) + "\n")

        print("\n[OK] Pipeline completed through NW4.")
        return 0


if __name__ == "__main__":
    raise SystemExit(run_pipeline())
