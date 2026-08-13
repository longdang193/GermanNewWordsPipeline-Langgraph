from __future__ import annotations

import json
import subprocess
import sys
import textwrap
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


def _make_stage(
    root: Path,
    calls: list[str],
    stage_id: str,
    *,
    dependencies: tuple[str, ...] = (),
    inputs: tuple[str, ...] = (),
    outputs: tuple[str, ...] = (),
    statuses: list[str] | None = None,
):
    remaining_statuses = list(statuses or ["completed"])

    def action(_log_fp):
        calls.append(stage_id)
        status = remaining_statuses.pop(0) if remaining_statuses else "completed"
        if status != "failed":
            for relative_path in outputs:
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"{stage_id}:{len(calls)}\n", encoding="utf-8")
        return run_full_pipeline.StageResult(status=status, detail=None)

    return run_full_pipeline.Stage(
        stage_id=stage_id,
        dependencies=dependencies,
        input_paths=tuple(Path(path) for path in inputs),
        output_paths=tuple(Path(path) for path in outputs),
        definition_paths=(),
        completion_policy="success",
        action=action,
    )


def _configure_stage_runner(monkeypatch, tmp_path: Path, stages) -> None:
    monkeypatch.setattr(run_full_pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(run_full_pipeline, "SCRIPTS", tmp_path / "Tools" / "scripts")
    monkeypatch.setattr(run_full_pipeline, "clear_proxy_env", lambda: None)
    monkeypatch.setattr(run_full_pipeline, "build_stages", lambda: stages)


def test_resume_skips_reusable_logical_stages(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "Inputs").mkdir()
    (tmp_path / "Inputs" / "words.md").write_text("eins\n", encoding="utf-8")
    calls: list[str] = []
    stages = [
        _make_stage(
            tmp_path,
            calls,
            "nw1_prepare",
            inputs=("Inputs/words.md",),
            outputs=("Outputs/01_words.md",),
        ),
        _make_stage(
            tmp_path,
            calls,
            "nw2_prepare",
            dependencies=("nw1_prepare",),
            inputs=("Outputs/01_words.md",),
            outputs=("Outputs/03_word_list.md",),
        ),
    ]
    _configure_stage_runner(monkeypatch, tmp_path, stages)

    assert run_full_pipeline.run_pipeline() == 0
    assert calls == ["nw1_prepare", "nw2_prepare"]

    state = json.loads((tmp_path / "Outputs" / "reports" / "pipeline_state.json").read_text(encoding="utf-8"))
    assert [stage["status"] for stage in state["stages"]] == ["completed", "completed"]

    calls.clear()
    assert run_full_pipeline.run_pipeline(resume=True) == 0
    assert calls == []


def test_resume_reruns_only_changed_stage_and_downstream(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "Inputs").mkdir()
    (tmp_path / "Inputs" / "words.md").write_text("eins\n", encoding="utf-8")
    calls: list[str] = []
    stages = [
        _make_stage(
            tmp_path,
            calls,
            "nw1_prepare",
            inputs=("Inputs/words.md",),
            outputs=("Outputs/01_words.md",),
        ),
        _make_stage(
            tmp_path,
            calls,
            "nw2_prepare",
            dependencies=("nw1_prepare",),
            inputs=("Outputs/01_words.md",),
            outputs=("Outputs/03_word_list.md",),
        ),
        _make_stage(
            tmp_path,
            calls,
            "nw3_nw4_finalize",
            dependencies=("nw2_prepare",),
            inputs=("Outputs/03_word_list.md",),
            outputs=("Outputs/06_words_final_fixed.md",),
        ),
    ]
    _configure_stage_runner(monkeypatch, tmp_path, stages)

    assert run_full_pipeline.run_pipeline() == 0
    calls.clear()
    (tmp_path / "Inputs" / "words.md").write_text("zwei\n", encoding="utf-8")

    assert run_full_pipeline.run_pipeline(resume=True) == 0
    assert calls == ["nw1_prepare", "nw2_prepare", "nw3_nw4_finalize"]


def test_resume_retries_failed_finalization_without_rerunning_upstream(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "Inputs").mkdir()
    (tmp_path / "Inputs" / "words.md").write_text("eins\n", encoding="utf-8")
    calls: list[str] = []
    stages = [
        _make_stage(
            tmp_path,
            calls,
            "nw1_prepare",
            inputs=("Inputs/words.md",),
            outputs=("Outputs/01_words.md",),
        ),
        _make_stage(
            tmp_path,
            calls,
            "nw2_prepare",
            dependencies=("nw1_prepare",),
            inputs=("Outputs/01_words.md",),
            outputs=("Outputs/03_word_list.md",),
        ),
        _make_stage(
            tmp_path,
            calls,
            "nw3_nw4_finalize",
            dependencies=("nw2_prepare",),
            inputs=("Outputs/03_word_list.md",),
            outputs=("Outputs/06_words_final_fixed.md",),
            statuses=["failed", "completed"],
        ),
    ]
    _configure_stage_runner(monkeypatch, tmp_path, stages)

    assert run_full_pipeline.run_pipeline() == 1
    assert calls == ["nw1_prepare", "nw2_prepare", "nw3_nw4_finalize"]

    calls.clear()
    assert run_full_pipeline.run_pipeline(resume=True) == 0
    assert calls == ["nw3_nw4_finalize"]


def test_resume_reuses_warning_stage(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "Inputs").mkdir()
    (tmp_path / "Inputs" / "words.md").write_text("eins\n", encoding="utf-8")
    calls: list[str] = []
    stages = [
        _make_stage(
            tmp_path,
            calls,
            "nw1_prepare",
            inputs=("Inputs/words.md",),
            outputs=("Outputs/01_words.md",),
            statuses=["completed_with_warnings"],
        ),
    ]
    _configure_stage_runner(monkeypatch, tmp_path, stages)

    assert run_full_pipeline.run_pipeline() == 0
    calls.clear()
    assert run_full_pipeline.run_pipeline(resume=True) == 0
    assert calls == []


def test_resume_retries_running_stage(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "Inputs").mkdir()
    (tmp_path / "Inputs" / "words.md").write_text("eins\n", encoding="utf-8")
    calls: list[str] = []
    stages = [
        _make_stage(
            tmp_path,
            calls,
            "nw1_prepare",
            inputs=("Inputs/words.md",),
            outputs=("Outputs/01_words.md",),
        ),
    ]
    _configure_stage_runner(monkeypatch, tmp_path, stages)

    assert run_full_pipeline.run_pipeline() == 0
    state_path = tmp_path / "Outputs" / "reports" / "pipeline_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["stages"][0]["status"] = "running"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    calls.clear()
    assert run_full_pipeline.run_pipeline(resume=True) == 0
    assert calls == ["nw1_prepare"]


def test_resume_rejects_corrupt_state_before_stage_runs(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []
    stages = [_make_stage(tmp_path, calls, "nw1_prepare", outputs=("Outputs/01_words.md",))]
    _configure_stage_runner(monkeypatch, tmp_path, stages)
    state_path = tmp_path / "Outputs" / "reports" / "pipeline_state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{broken", encoding="utf-8")

    assert run_full_pipeline.run_pipeline(resume=True) == 2
    assert calls == []


def test_resume_rejects_second_process_holding_lock(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []
    stages = [_make_stage(tmp_path, calls, "nw1_prepare", outputs=("Outputs/01_words.md",))]
    _configure_stage_runner(monkeypatch, tmp_path, stages)
    lock_path = tmp_path / "Outputs" / "reports" / "pipeline_state.lock"
    script_dir = Path(run_full_pipeline.__file__).resolve().parent
    tools_dir = script_dir.parent
    source_dir = tools_dir / "src"
    child = textwrap.dedent(
        f"""
        import sys
        import time
        from pathlib import Path
        sys.path[:0] = [{str(script_dir)!r}, {str(tools_dir)!r}, {str(source_dir)!r}]
        import run_full_pipeline
        with run_full_pipeline.pipeline_lock(Path(sys.argv[1])):
            print('locked', flush=True)
            time.sleep(10)
        """
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", child, str(lock_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        assert proc.stdout.readline().strip() == "locked"
        assert run_full_pipeline.run_pipeline(resume=True) == 2
        assert calls == []
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_pipeline_continues_when_nw1_nonzero_but_blocks_exist(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    (root / "Outputs").mkdir(parents=True, exist_ok=True)
    qa_script = root / "Tools" / "scripts" / "nw1_qa_review.py"
    qa_script.parent.mkdir(parents=True, exist_ok=True)
    qa_script.write_text("", encoding="utf-8")
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
        if desc == "NW1: QA review":
            report = root / "Outputs" / "reports" / "nw1_qa_latest.json"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("{}\n", encoding="utf-8")
        output_by_step = {
            "NW2: Normalize words": "Outputs/02_words_fixed.md",
            "NW2: Extract word list": "Outputs/03_word_list.md",
            "NW3: Query NotebookLM (stdio) and generate Outputs/04_see_also.md": "Outputs/04_see_also.md",
            "NW3: Preprocess see_also": "Outputs/05_see_also_fixed.md",
            "NW3: Merge see_also": "Outputs/06_words_final.md",
            "NW4: Normalize see_also references": "Outputs/06_words_final_fixed.md",
        }
        if desc in output_by_step:
            output_path = root / output_by_step[desc]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"{desc}\n", encoding="utf-8")
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
