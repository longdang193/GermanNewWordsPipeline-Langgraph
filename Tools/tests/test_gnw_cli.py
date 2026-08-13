from __future__ import annotations

import builtins
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "Tools" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import gnw.__main__ as gnw_main  # noqa: E402


def test_cmd_auth_uses_shared_notebooklm_runner(monkeypatch, tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def fake_auth(*, cwd: Path, file_mode: bool = False) -> int:
        seen["cwd"] = cwd
        seen["file_mode"] = file_mode
        return 7

    monkeypatch.setattr(gnw_main, "run_notebooklm_auth", fake_auth, raising=False)
    monkeypatch.setattr(
        gnw_main.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy auth launched")),
    )
    args = type("Args", (), {"root": tmp_path, "file_mode": True, "clear_proxy": False})()

    assert gnw_main.cmd_auth(args) == 7
    assert seen == {"cwd": tmp_path, "file_mode": True}


def test_cmd_doctor_reports_notebooklm_install_problems(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gnw_main.shutil, "which", lambda name: "C:/Windows/py.exe" if name == "py" else None)
    monkeypatch.setattr(
        gnw_main,
        "notebooklm_install_problems",
        lambda: ["requires nlm >= 0.9.4"],
        raising=False,
    )

    assert gnw_main.cmd_doctor(type("Args", (), {})()) == 2
    assert "[FAIL] requires nlm >= 0.9.4" in capsys.readouterr().out


def test_cmd_doctor_accepts_coherent_notebooklm_install(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gnw_main.shutil, "which", lambda name: "C:/Windows/py.exe" if name == "py" else None)
    monkeypatch.setattr(gnw_main, "notebooklm_install_problems", lambda: [], raising=False)

    assert gnw_main.cmd_doctor(type("Args", (), {})()) == 0
    assert "[OK] Basic executables present in PATH" in capsys.readouterr().out


def test_cmd_run_flushes_step_banner_in_script_runner(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    script = root / "Tools" / "scripts" / "run_full_pipeline.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("print('ok')\n", encoding="utf-8")

    printed: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_print(*args: object, **kwargs: object) -> None:
        printed.append((args, dict(kwargs)))

    real_import = builtins.__import__

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        if name == "gnw_pipeline.langgraph_app":
            raise ModuleNotFoundError(name)
        return real_import(name, globals, locals, fromlist, level)

    class Result:
        returncode = 0

    monkeypatch.setattr(builtins, "print", fake_print)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(gnw_main, "sys", type("SysStub", (), {"executable": sys.executable, "frozen": False})())
    monkeypatch.setattr(gnw_main.subprocess, "run", lambda *args, **kwargs: Result())

    args = type("Args", (), {"root": root, "clear_proxy": False})()

    assert gnw_main.cmd_run(args) == 0
    assert printed == [(("[STEP] Run full pipeline NW1->NW4 (script runner)",), {"flush": True})]


def test_cmd_run_forwards_resume_without_importing_langgraph(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    script = root / "Tools" / "scripts" / "run_full_pipeline.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("print('ok')\n", encoding="utf-8")
    calls: list[list[str]] = []
    real_import = builtins.__import__

    def fail_langgraph_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        if name == "gnw_pipeline.langgraph_app":
            raise AssertionError("public CLI must not import LangGraph runner")
        return real_import(name, globals, locals, fromlist, level)

    class Result:
        returncode = 0

    monkeypatch.setattr(builtins, "__import__", fail_langgraph_import)
    monkeypatch.setattr(
        gnw_main.subprocess,
        "run",
        lambda cmd, **_kwargs: calls.append(cmd) or Result(),
    )
    args = type("Args", (), {"root": root, "clear_proxy": False, "resume": True})()

    assert gnw_main.cmd_run(args) == 0
    assert calls == [[sys.executable, str(script), "--resume"]]


def test_run_parser_accepts_resume_flag(tmp_path: Path) -> None:
    args = gnw_main.build_parser().parse_args(["--root", str(tmp_path), "run", "--resume"])

    assert args.resume is True
