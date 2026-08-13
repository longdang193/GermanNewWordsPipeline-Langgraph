from __future__ import annotations

import builtins
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "Tools" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import gnw.ui as ui  # noqa: E402


def test_run_pipeline_forwards_resume(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "Tools" / "scripts" / "run_full_pipeline.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("print('ok')\n", encoding="utf-8")
    calls: list[list[str]] = []

    class Result:
        returncode = 0

    monkeypatch.setattr(ui.subprocess, "run", lambda cmd, **_kwargs: calls.append(cmd) or Result())
    monkeypatch.setattr(ui.sys, "frozen", False, raising=False)

    assert ui.run_pipeline(tmp_path, resume=True) == 0
    assert calls == [[sys.executable, str(script), "--resume"]]


def test_ui_resume_action_forwards_explicit_intent(monkeypatch, tmp_path: Path) -> None:
    word_list = tmp_path / "Inputs" / "Word List (DE).md"
    word_list.parent.mkdir(parents=True, exist_ok=True)
    word_list.write_text("eins\n", encoding="utf-8")
    calls: list[bool] = []
    answers = iter(["r", "q"])

    monkeypatch.setattr(ui, "run_pipeline", lambda _root, *, resume=False: calls.append(resume) or 0)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    assert ui.run_ui(tmp_path) == 0
    assert calls == [True]


def test_ui_completion_can_open_outputs(monkeypatch, tmp_path: Path) -> None:
    word_list = tmp_path / "Inputs" / "Word List (DE).md"
    word_list.parent.mkdir(parents=True, exist_ok=True)
    word_list.write_text("eins\n", encoding="utf-8")
    opened: list[Path] = []
    prompts: list[str] = []
    answers = iter(["1", "o", "q"])

    monkeypatch.setattr(ui, "run_pipeline", lambda _root, *, resume=False: 0)
    monkeypatch.setattr(ui, "open_outputs_folder", opened.append)
    monkeypatch.setattr(
        builtins,
        "input",
        lambda prompt="": prompts.append(prompt) or next(answers),
    )

    assert ui.run_ui(tmp_path) == 0
    assert opened == [tmp_path]
    assert "Enter=menu | O=open Outputs | Q=exit > " in prompts
