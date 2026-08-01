from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

NOTEBOOKLM_MCP_MIN_VERSION = (0, 9, 4)

_COMMAND_NAMES = ("nlm", "notebooklm-mcp")
_PROXY_NAMES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)
_VERSION_RE = re.compile(r"\bnlm version (\d+)\.(\d+)\.(\d+)\b", re.IGNORECASE)


def _inspect_notebooklm_install() -> tuple[dict[str, Path], list[str]]:
    commands: dict[str, Path] = {}
    problems: list[str] = []

    for name in _COMMAND_NAMES:
        resolved = shutil.which(name)
        if resolved is None:
            problems.append(f"missing executable in PATH: {name}")
        else:
            commands[name] = Path(resolved).resolve()

    nlm = commands.get("nlm")
    if nlm is not None:
        try:
            result = subprocess.run(
                [str(nlm), "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            problems.append("nlm --version timed out after 10 seconds")
        except OSError as error:
            problems.append(f"could not run nlm --version: {error}")
        else:
            output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
            if result.returncode != 0:
                problems.append(f"nlm --version exited with code {result.returncode}: {output}")
            else:
                match = _VERSION_RE.search(output)
                if match is None:
                    problems.append(f"unrecognized nlm version output: {output or '<empty>'}")
                else:
                    version = tuple(int(part) for part in match.groups())
                    if version < NOTEBOOKLM_MCP_MIN_VERSION:
                        minimum = ".".join(str(part) for part in NOTEBOOKLM_MCP_MIN_VERSION)
                        problems.append(f"requires nlm >= {minimum}; found {'.'.join(match.groups())}")

    if len(commands) == len(_COMMAND_NAMES):
        directories = {os.path.normcase(str(path.parent)) for path in commands.values()}
        if len(directories) != 1:
            paths = ", ".join(f"{name}={commands[name]}" for name in _COMMAND_NAMES)
            problems.append(f"mixed NotebookLM command providers: {paths}")

    if problems:
        problems.extend(
            (
                "remove legacy tool: uv tool uninstall notebooklm-mcp-server",
                "install supported tool: uv tool install --force notebooklm-mcp-cli",
            )
        )

    return commands, problems


def notebooklm_install_problems() -> list[str]:
    return _inspect_notebooklm_install()[1]


def run_notebooklm_auth(*, cwd: Path, file_mode: bool = False) -> int:
    commands, problems = _inspect_notebooklm_install()
    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}")
        return 2

    nlm = commands.get("nlm")
    if nlm is None:
        print("[FAIL] missing executable in PATH: nlm")
        return 2

    env = os.environ.copy()
    for name in _PROXY_NAMES:
        env[name] = ""

    command = [str(nlm), "login"]
    if file_mode:
        command.append("--manual")

    print("[STEP] NotebookLM MCP auth (interactive if needed)")
    try:
        return subprocess.run(command, cwd=str(cwd), env=env, check=False).returncode
    except OSError as error:
        print(f"[FAIL] Could not start NotebookLM login: {error}")
        return 2
