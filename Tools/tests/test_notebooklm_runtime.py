from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "Tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
SRC_DIR = ROOT / "Tools" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
SCRIPTS_DIR = ROOT / "Tools" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from scripts import generate_requirement3_notebooklm as nw3  # noqa: E402
from gnw_pipeline import notebooklm_runtime  # noqa: E402


def _commands(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    return {
        "nlm": str(bin_dir / "nlm.exe"),
        "notebooklm-mcp": str(bin_dir / "notebooklm-mcp.exe"),
    }


def _patch_commands(monkeypatch, commands: dict[str, str]) -> None:
    monkeypatch.setattr(notebooklm_runtime.shutil, "which", commands.get)


def test_install_accepts_minimum_and_newer_versions(monkeypatch, tmp_path: Path) -> None:
    _patch_commands(monkeypatch, _commands(tmp_path))

    for version in ("0.9.4", "1.2.3"):
        monkeypatch.setattr(
            notebooklm_runtime.subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout=f"nlm version {version}\n", stderr=""
            ),
        )
        assert notebooklm_runtime.notebooklm_install_problems() == []


def test_install_rejects_missing_old_and_malformed_nlm(monkeypatch, tmp_path: Path) -> None:
    commands = _commands(tmp_path)
    commands.pop("nlm")
    _patch_commands(monkeypatch, commands)
    assert any("missing executable in PATH: nlm" in p for p in notebooklm_runtime.notebooklm_install_problems())

    commands = _commands(tmp_path)
    _patch_commands(monkeypatch, commands)
    for output, expected in (("nlm version 0.9.3", "requires nlm >= 0.9.4"), ("unknown", "unrecognized nlm version")):
        monkeypatch.setattr(
            notebooklm_runtime.subprocess,
            "run",
            lambda *args, output=output, **kwargs: subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout=output, stderr=""
            ),
        )
        assert any(expected in p for p in notebooklm_runtime.notebooklm_install_problems())


def test_install_rejects_mixed_command_directories(monkeypatch, tmp_path: Path) -> None:
    commands = _commands(tmp_path)
    commands["notebooklm-mcp"] = str(tmp_path / "other" / "notebooklm-mcp.exe")
    _patch_commands(monkeypatch, commands)
    monkeypatch.setattr(
        notebooklm_runtime.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="nlm version 0.9.4", stderr=""
        ),
    )

    assert any("mixed NotebookLM command providers" in p for p in notebooklm_runtime.notebooklm_install_problems())


def test_install_reports_version_timeout_and_launch_error(monkeypatch, tmp_path: Path) -> None:
    _patch_commands(monkeypatch, _commands(tmp_path))

    for error, expected in (
        (subprocess.TimeoutExpired(["nlm", "--version"], 10), "timed out"),
        (OSError("blocked"), "could not run nlm --version"),
    ):
        def fail(*args, error=error, **kwargs):
            raise error

        monkeypatch.setattr(notebooklm_runtime.subprocess, "run", fail)
        assert any(expected in p for p in notebooklm_runtime.notebooklm_install_problems())

    monkeypatch.setattr(
        notebooklm_runtime.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=1, stdout="", stderr="version failed"
        ),
    )
    assert any(
        "nlm --version exited with code 1" in problem
        for problem in notebooklm_runtime.notebooklm_install_problems()
    )


def test_auth_does_not_launch_when_install_is_invalid(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        notebooklm_runtime,
        "_inspect_notebooklm_install",
        lambda: ({}, ["missing executable in PATH: nlm"]),
    )
    monkeypatch.setattr(
        notebooklm_runtime.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("auth launched")),
    )

    assert notebooklm_runtime.run_notebooklm_auth(cwd=tmp_path) == 2


def test_auth_clears_child_proxies_and_forwards_file_mode(monkeypatch, tmp_path: Path) -> None:
    nlm = tmp_path / "bin" / "nlm.exe"
    monkeypatch.setattr(
        notebooklm_runtime,
        "_inspect_notebooklm_install",
        lambda: ({"nlm": nlm}, []),
    )
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid")
    seen: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = kwargs["env"]
        seen["stderr"] = kwargs["stderr"]
        return subprocess.CompletedProcess(args=cmd, returncode=7)

    monkeypatch.setattr(notebooklm_runtime.subprocess, "run", fake_run)

    assert notebooklm_runtime.run_notebooklm_auth(cwd=tmp_path, file_mode=True) == 7
    assert seen["cmd"] == [str(nlm), "login", "--manual"]
    child_env = seen["env"]
    assert isinstance(child_env, dict)
    assert child_env["HTTP_PROXY"] == ""
    assert child_env["NO_COLOR"] == "1"
    assert seen["stderr"] is subprocess.STDOUT
    assert os.environ["HTTP_PROXY"] == "http://proxy.invalid"


def test_auth_launch_error_returns_two(monkeypatch, tmp_path: Path) -> None:
    nlm = tmp_path / "bin" / "nlm.exe"
    monkeypatch.setattr(
        notebooklm_runtime,
        "_inspect_notebooklm_install",
        lambda: ({"nlm": nlm}, []),
    )
    monkeypatch.setattr(
        notebooklm_runtime.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("blocked")),
    )

    assert notebooklm_runtime.run_notebooklm_auth(cwd=tmp_path) == 2


def test_nw3_rejects_incompatible_install_before_reading_words(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    word_list = tmp_path / "03_word_list.md"
    word_list.write_text("- Beispiel\n", encoding="utf-8")
    monkeypatch.setattr(nw3, "WORDLIST_PATH", word_list)
    monkeypatch.setattr(
        nw3,
        "notebooklm_install_problems",
        lambda: ["requires nlm >= 0.9.4"],
        raising=False,
    )
    monkeypatch.setattr(
        nw3,
        "read_words",
        lambda: (_ for _ in ()).throw(AssertionError("words read before preflight")),
    )

    assert nw3.main() == 2
    assert "[error] requires nlm >= 0.9.4" in capsys.readouterr().out
