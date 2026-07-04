from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "Tools"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
SCRIPTS_MODULE_DIR = ROOT / "Tools" / "scripts"
if str(SCRIPTS_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_MODULE_DIR))

import scripts.run_full_pipeline as run_full_pipeline


def test_pipeline_continues_when_nw1_nonzero_but_blocks_exist(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    (root / "Outputs").mkdir(parents=True, exist_ok=True)
    calls: list[str] = []

    monkeypatch.setattr(run_full_pipeline, "ROOT", root)
    monkeypatch.setattr(run_full_pipeline, "SCRIPTS", root / "Tools" / "scripts")
    monkeypatch.setattr(run_full_pipeline, "clear_proxy_env", lambda: None)
    monkeypatch.setattr(run_full_pipeline, "compute_run_id", lambda: "rid")
    monkeypatch.setattr(run_full_pipeline, "compute_prompt_hashes", lambda: {})
    monkeypatch.setattr(run_full_pipeline, "count_word_list_entries", lambda _path: 1)

    def fake_run_cmd(cmd: list[str], desc: str, **_kwargs):
        calls.append(desc)
        class Result:
            def __init__(self, returncode: int = 0):
                self.returncode = returncode
                self.stdout = ""
                self.stderr = ""
        if desc == "NW1: Generate Outputs/01_words.md":
            (root / "Outputs" / "01_words.md").write_text(
                "TARGET DECK: TEST\n\n"
                "SSTART\n%VOCAB (German) ver 3\nword: Alpha\nmeaning: Alpha = erste Sache / first thing\nde_1: Alpha ist wichtig.\nen_1: Alpha is important.\nword_inf: Alpha\nTags: noun\nEEND\n",
                encoding="utf-8",
            )
            return Result(1)
        if desc == "NW1: Validate Outputs/01_words.md":
            return Result(1)
        return Result(0)

    monkeypatch.setattr(run_full_pipeline, "run_cmd", fake_run_cmd)

    result = run_full_pipeline.run_pipeline()

    assert result == 0
    assert "NW2: Normalize words" in calls
    assert any(desc.startswith("NW3:") for desc in calls)


def test_pipeline_stops_when_nw1_nonzero_and_no_blocks_exist(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    (root / "Outputs").mkdir(parents=True, exist_ok=True)
    calls: list[str] = []

    monkeypatch.setattr(run_full_pipeline, "ROOT", root)
    monkeypatch.setattr(run_full_pipeline, "SCRIPTS", root / "Tools" / "scripts")
    monkeypatch.setattr(run_full_pipeline, "clear_proxy_env", lambda: None)
    monkeypatch.setattr(run_full_pipeline, "compute_run_id", lambda: "rid")
    monkeypatch.setattr(run_full_pipeline, "compute_prompt_hashes", lambda: {})

    def fake_run_cmd(cmd: list[str], desc: str, **_kwargs):
        calls.append(desc)
        class Result:
            def __init__(self, returncode: int = 0):
                self.returncode = returncode
                self.stdout = ""
                self.stderr = ""
        if desc == "NW1: Generate Outputs/01_words.md":
            (root / "Outputs" / "01_words.md").write_text("TARGET DECK: TEST\n\n## UNRESOLVED PART\n", encoding="utf-8")
            return Result(1)
        return Result(0)

    monkeypatch.setattr(run_full_pipeline, "run_cmd", fake_run_cmd)

    result = run_full_pipeline.run_pipeline()

    assert result == 1
    assert "NW2: Normalize words" not in calls
