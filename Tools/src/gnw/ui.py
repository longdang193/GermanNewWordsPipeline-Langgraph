from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UiState:
    last_word_list_path: str | None = None


def _state_path(root: Path) -> Path:
    return root / "Outputs" / "reports" / "ui_state.json"


def load_state(root: Path) -> UiState:
    path = _state_path(root)
    if not path.exists():
        return UiState()
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return UiState()
    if not isinstance(obj, dict):
        return UiState()
    v = obj.get("last_word_list_path")
    return UiState(last_word_list_path=v if isinstance(v, str) else None)


def save_state(root: Path, state: UiState) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"last_word_list_path": state.last_word_list_path}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _pause(message: str = "Press Enter to continue...") -> None:
    try:
        input(f"\n{message}")
    except Exception:
        pass


def _read_path(prompt: str) -> Path:
    raw = input(prompt).strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        raw = raw[1:-1]
    return Path(raw).expanduser()


def open_outputs_folder(root: Path) -> None:
    outputs = root / "Outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["explorer.exe", str(outputs)], check=False)
    except Exception:
        print(f"[FAIL] Cannot open folder: {outputs}")


def run_notebooklm_auth(root: Path) -> int:
    env = os.environ.copy()
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if env.get(k):
            env[k] = ""
    print("[STEP] NotebookLM MCP auth (interactive if needed)")
    proc = subprocess.run(["notebooklm-mcp-auth"], cwd=str(root), env=env)
    return proc.returncode


def _python_launcher() -> str | None:
    for exe in ("py", "python", "python3"):
        found = shutil.which(exe)
        if found:
            return found
    return None


def run_pipeline(root: Path) -> int:
    script = root / "Tools" / "scripts" / "run_full_pipeline.py"
    if not script.exists():
        print(f"[FAIL] Missing pipeline runner: {script}")
        return 2

    env = os.environ.copy()
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if env.get(k):
            env[k] = ""

    if getattr(sys, "frozen", False):
        launcher = _python_launcher()
        if not launcher:
            print("[FAIL] Missing Python launcher (py/python).")
            return 2
        cmd = [launcher, str(script)]
    else:
        cmd = [sys.executable, str(script)]

    print("[STEP] Run pipeline (NW1->NW4)")
    proc = subprocess.run(cmd, cwd=str(root), env=env)
    return int(proc.returncode)


def set_word_list_path(root: Path, state: UiState) -> UiState:
    print("\nEnter path to word list file (Markdown).")
    path = _read_path("> ")
    if not path.exists():
        print(f"[FAIL] File not found: {path}")
        _pause()
        return state
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        print(f"[FAIL] File empty: {path}")
        _pause()
        return state

    dst = root / "Inputs" / "Word List (DE).md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    bak = dst.with_suffix(".bak")
    if dst.exists():
        try:
            bak.write_text(dst.read_text(encoding="utf-8", errors="replace"), encoding="utf-8", newline="\n")
        except Exception:
            pass
    dst.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[OK] Set input list: {dst}")
    return UiState(last_word_list_path=str(path))


def _menu_render(root: Path, state: UiState) -> None:
    print("\n" + "=" * 60)
    print("GermanNewWords")
    print("=" * 60)
    print(f"Root: {root}")
    print(f"Input: {root / 'Inputs' / 'Word List (DE).md'}")
    if state.last_word_list_path:
        print(f"Last external list: {state.last_word_list_path}")
    print("-" * 60)
    print("1) Run pipeline")
    print("2) Set word list path")
    print("3) Auth NotebookLM")
    print("4) Open Outputs folder")
    print("5) Exit")


def run_ui(root: Path) -> int:
    state = load_state(root)
    while True:
        _menu_render(root, state)
        try:
            choice = input("> ").strip().lower()
        except EOFError:
            return 0

        if choice in {"5", "q", "quit", "exit"}:
            return 0

        if choice == "4":
            open_outputs_folder(root)
            continue

        if choice == "3":
            rc = run_notebooklm_auth(root)
            if rc != 0:
                print(f"[FAIL] Auth failed (exit={rc})")
                _pause()
            continue

        if choice == "2":
            state = set_word_list_path(root, state)
            save_state(root, state)
            continue

        if choice == "1":
            inputs_path = root / "Inputs" / "Word List (DE).md"
            if not inputs_path.exists() or not inputs_path.read_text(encoding="utf-8", errors="replace").strip():
                print("[FAIL] Missing/empty Inputs/Word List (DE).md. Use 'Set word list path' first.")
                _pause()
                continue

            rc = run_pipeline(root)
            final_md = root / "Outputs" / "06_words_final_fixed.md"
            log_path = root / "Outputs" / "logs" / "run_latest.log"
            report_path = root / "Outputs" / "reports" / "run_latest.json"
            print("\n" + "-" * 60)
            if rc == 0 and final_md.exists():
                print("[OK] Run complete.")
            else:
                print(f"[FAIL] Run failed (exit={rc}).")
            print(f"Final:  {final_md}")
            print(f"Log:    {log_path}")
            print(f"Report: {report_path}")
            print("-" * 60)
            again = input("Enter=menu | Q=exit > ").strip().lower()
            if again in {"q", "quit", "exit"}:
                return rc
            continue

        print("[WARN] Unknown choice.")
