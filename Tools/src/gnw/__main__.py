from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """Find repo root by walking upward from start.

    Heuristic: repo root contains Tools/scripts/run_full_pipeline.py and Inputs/.
    Fall back to start when not found.
    """
    cur = start.resolve()
    for _ in range(8):
        if (cur / "Tools" / "scripts" / "run_full_pipeline.py").exists() and (cur / "Inputs").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def default_root() -> Path:
    env_root = os.environ.get("GNW_ROOT")
    if env_root:
        return Path(env_root)
    start = Path.cwd()
    # Double-click runs with unpredictable CWD (often System32). Prefer exe location.
    if getattr(sys, "frozen", False):
        try:
            start = Path(sys.executable).resolve().parent
        except Exception:
            start = Path.cwd()
    return find_repo_root(start)


def _run(cmd: list[str], *, cwd: Path) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd))
    return proc.returncode


def cmd_check_input(args: argparse.Namespace) -> int:
    root = args.root
    word_list = root / "Inputs" / "Word List (DE).md"
    if not word_list.exists():
        print(f"[FAIL] Missing input file: {word_list}")
        return 2
    text = word_list.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        print(f"[FAIL] Empty input file: {word_list}")
        return 2
    print(f"[OK] Input file present: {word_list}")
    return 0


def cmd_auth(args: argparse.Namespace) -> int:
    root = args.root
    env = os.environ.copy()
    if args.clear_proxy:
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env[k] = ""
    cmd = ["notebooklm-mcp-auth"]
    if args.file_mode:
        cmd.append("--file")
    print("[STEP] NotebookLM MCP auth (interactive if needed)")
    return subprocess.run(cmd, cwd=str(root), env=env).returncode


def cmd_run(args: argparse.Namespace) -> int:
    root = args.root
    env = os.environ.copy()
    if args.clear_proxy:
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env[k] = ""
    try:
        from gnw_pipeline.langgraph_app import run as run_graph  # type: ignore[import-not-found]

        print("[STEP] Run full pipeline NW1->NW4 (LangGraph)")
        run_graph(root=root, clear_proxy=args.clear_proxy)
        return 0
    except ModuleNotFoundError:
        script = root / "Tools" / "scripts" / "run_full_pipeline.py"
        if not script.exists():
            print(f"[FAIL] Missing pipeline runner: {script}")
            return 2
        print("[STEP] Run full pipeline NW1->NW4 (script runner)")
        # In a frozen exe, sys.executable points back to the exe (would recurse).
        if getattr(sys, "frozen", False):
            py_launcher = shutil.which("py") or shutil.which("python") or shutil.which("python3")
            if not py_launcher:
                print("[FAIL] No Python launcher found (py/python).")
                print("       Install Python 3.11+ or run pipeline from repo using Python.")
                return 2
            return subprocess.run([py_launcher, str(script)], cwd=str(root), env=env).returncode
        return subprocess.run([sys.executable, str(script)], cwd=str(root), env=env).returncode


def cmd_doctor(_: argparse.Namespace) -> int:
    problems: list[str] = []
    for exe in ("notebooklm-mcp", "notebooklm-mcp-auth", "py"):
        if shutil.which(exe) is None:
            problems.append(f"missing executable in PATH: {exe}")
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        return 2
    print("[OK] Basic executables present in PATH")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gnw", description="German_NewWords minimal executable.")
    p.add_argument(
        "--root",
        type=Path,
        default=default_root(),
        help="Repo root (default: auto-detect from CWD or GNW_ROOT).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s_check = sub.add_parser("check-input", help="Verify Inputs/Word List (DE).md exists and non-empty.")
    s_check.set_defaults(fn=cmd_check_input)

    s_auth = sub.add_parser("auth", help="Run notebooklm-mcp auth (no cookie file juggling).")
    s_auth.add_argument("--file", dest="file_mode", action="store_true", help="Use --file mode if needed.")
    s_auth.add_argument(
        "--clear-proxy",
        action="store_true",
        help="Clear HTTP(S)_PROXY/ALL_PROXY env for this command only.",
    )
    s_auth.set_defaults(fn=cmd_auth)

    s_run = sub.add_parser("run", help="Run NW1->NW4 pipeline.")
    s_run.add_argument(
        "--clear-proxy",
        action="store_true",
        help="Clear HTTP(S)_PROXY/ALL_PROXY env for this command only.",
    )
    s_run.set_defaults(fn=cmd_run)

    s_doc = sub.add_parser("doctor", help="Check required executables in PATH.")
    s_doc.set_defaults(fn=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    raw_argv = list(argv) if argv is not None else list(sys.argv[1:])

    # Minimal UX: double-click `.exe` launches UI menu by default.
    if getattr(sys, "frozen", False) and (raw_argv is None or len(raw_argv) == 0):
        root = default_root()
        try:
            from gnw.ui import run_ui

            raise SystemExit(run_ui(root))
        except SystemExit:
            raise
        except Exception:
            import traceback

            traceback.print_exc()
            try:
                input("\n[FAIL] Press Enter to close...")
            except Exception:
                pass
            raise

    try:
        args = parser.parse_args(raw_argv)
        fn = getattr(args, "fn")
        rc = fn(args)
    except SystemExit as exc:
        if getattr(sys, "frozen", False) and (getattr(exc, "code", 1) or 0) != 0:
            try:
                input("\n[FAIL] Press Enter to close...")
            except Exception:
                pass
        raise
    except Exception:
        if getattr(sys, "frozen", False):
            import traceback

            traceback.print_exc()
            try:
                input("\n[FAIL] Press Enter to close...")
            except Exception:
                pass
        raise

    if getattr(sys, "frozen", False) and rc != 0:
        try:
            input("\n[FAIL] Press Enter to close...")
        except Exception:
            pass
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
