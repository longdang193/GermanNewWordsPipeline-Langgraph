#!/usr/bin/env python3
"""Run NW1 through NW4 with resumable logical stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Literal, TextIO

from notebooklm_errors import classify_notebooklm_error
from gnw_pipeline.notebooklm_runtime import run_notebooklm_auth
from gnw_pipeline.nw1_steps import build_nw1_steps, has_parseable_nw1_blocks

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "Tools" / "scripts"
STATE_SCHEMA_VERSION = 1
COMPLETED_STATUSES = {"completed", "completed_with_warnings"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


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
        path = ROOT / rel
        value = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "<MISSING>"
        parts.append(f"## {rel}\n{value}\n")
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
        path = ROOT / rel
        out[rel] = _hash_path(path) if path.exists() else "<MISSING>"
    return out


def clear_proxy_env() -> None:
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if os.environ.get(key):
            os.environ[key] = ""


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
    proc = subprocess.run(cmd, cwd=str(cwd or ROOT), text=True, capture_output=True)
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


def count_word_list_entries(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip().startswith("- "))


StageStatus = Literal["completed", "completed_with_warnings", "failed"]


@dataclass(frozen=True)
class StageResult:
    status: StageStatus
    detail: str | None


@dataclass(frozen=True)
class Stage:
    stage_id: str
    dependencies: tuple[str, ...]
    input_paths: tuple[Path, ...]
    output_paths: tuple[Path, ...]
    definition_paths: tuple[Path, ...]
    completion_policy: str
    action: Callable[[TextIO], StageResult]


class PipelineStateError(RuntimeError):
    pass


class PipelineLockError(RuntimeError):
    pass


def _absolute(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _path_key(path: Path) -> str:
    return path.as_posix()


def _hash_path(path: Path) -> str:
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as fp:
            for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(child.relative_to(path).as_posix().encode("utf-8"))
            digest.update(_hash_path(child).encode("ascii"))
        return digest.hexdigest()
    return "<MISSING>"


def _fingerprint_paths(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(_path_key(path).encode("utf-8"))
        digest.update(_hash_path(_absolute(path)).encode("ascii"))
    return digest.hexdigest()


def _definition_fingerprint(stage: Stage) -> str:
    digest = hashlib.sha256()
    digest.update(stage.stage_id.encode("utf-8"))
    digest.update("\n".join(stage.dependencies).encode("utf-8"))
    digest.update(stage.completion_policy.encode("utf-8"))
    digest.update(_fingerprint_paths(stage.definition_paths).encode("ascii"))
    return digest.hexdigest()


def _input_fingerprint(stage: Stage, records: dict[str, dict[str, object]]) -> str:
    digest = hashlib.sha256()
    digest.update(_fingerprint_paths(stage.input_paths).encode("ascii"))
    for dependency in stage.dependencies:
        output_fingerprints = records[dependency].get("output_fingerprints")
        digest.update(dependency.encode("utf-8"))
        digest.update(json.dumps(output_fingerprints, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def _output_fingerprints(stage: Stage) -> dict[str, str] | None:
    out: dict[str, str] = {}
    for path in stage.output_paths:
        full_path = _absolute(path)
        if not full_path.exists():
            return None
        out[_path_key(path)] = _hash_path(full_path)
    return out


def _record_for(stage: Stage) -> dict[str, object]:
    return {
        "id": stage.stage_id,
        "dependencies": list(stage.dependencies),
        "status": "pending",
        "definition_fingerprint": None,
        "input_fingerprint": None,
        "output_fingerprints": None,
        "started_at_utc": None,
        "finished_at_utc": None,
        "exit_code": None,
        "detail": None,
    }


def _initial_state(stages: list[Stage]) -> dict[str, object]:
    return {"schema_version": STATE_SCHEMA_VERSION, "stages": [_record_for(stage) for stage in stages]}


def _write_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def _load_state(path: Path) -> dict[str, object]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineStateError(f"Cannot read resume state: {path}. Remove it to start fresh.") from exc
    if not isinstance(loaded, dict) or loaded.get("schema_version") != STATE_SCHEMA_VERSION:
        raise PipelineStateError(f"Unsupported resume state: {path}. Remove it to start fresh.")
    if not isinstance(loaded.get("stages"), list):
        raise PipelineStateError(f"Invalid resume state: {path}. Remove it to start fresh.")
    return loaded


def _records_for(state: dict[str, object], stages: list[Stage]) -> dict[str, dict[str, object]]:
    existing = {
        record.get("id"): record
        for record in state["stages"]
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    records: dict[str, dict[str, object]] = {}
    ordered: list[dict[str, object]] = []
    for stage in stages:
        record = existing.get(stage.stage_id)
        if not isinstance(record, dict):
            record = _record_for(stage)
        records[stage.stage_id] = record
        ordered.append(record)
    state["stages"] = ordered
    return records


@contextmanager
def pipeline_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = path.open("a+b")
    if path.stat().st_size == 0:
        lock_file.write(b"0")
        lock_file.flush()
    lock_file.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        lock_file.close()
        raise PipelineLockError("Another pipeline run is active.") from exc
    try:
        yield
    finally:
        lock_file.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


def _is_reusable(
    stage: Stage,
    record: dict[str, object],
    records: dict[str, dict[str, object]],
    rerun_stage_ids: set[str],
) -> bool:
    if any(dependency in rerun_stage_ids for dependency in stage.dependencies):
        return False
    if record.get("status") not in COMPLETED_STATUSES:
        return False
    if record.get("definition_fingerprint") != _definition_fingerprint(stage):
        return False
    if record.get("input_fingerprint") != _input_fingerprint(stage, records):
        return False
    outputs = _output_fingerprints(stage)
    if outputs is None or record.get("output_fingerprints") != outputs:
        return False
    return all(records[dependency].get("status") in COMPLETED_STATUSES for dependency in stage.dependencies)


def _run_nw1_prepare(log_fp: TextIO) -> StageResult:
    outputs_word_file = ROOT / "Outputs" / "01_words.md"
    if outputs_word_file.exists():
        outputs_word_file.unlink()
    legacy_word_file = ROOT / "01_words.md"
    if legacy_word_file.exists():
        legacy_word_file.unlink()

    warnings: list[str] = []
    nw1_generate, nw1_validate, nw1_qa_review = build_nw1_steps(root=ROOT)
    nw1 = run_cmd(nw1_generate.cmd, "NW1: Generate Outputs/01_words.md", log_fp=log_fp)
    if nw1.returncode != 0:
        if not has_parseable_nw1_blocks(outputs_word_file):
            print("\n[STOP] NW1 generation failed. Fix NW1 generation quality first.")
            return StageResult("failed", "NW1 generation produced no usable blocks.")
        print("\n[WARN] NW1 exited non-zero, but usable blocks exist. Continuing.")
        warnings.append("NW1 generation exited non-zero with usable blocks.")

    validation = run_cmd(nw1_validate.cmd, "NW1: Validate Outputs/01_words.md", log_fp=log_fp)
    if validation.returncode != 0:
        if not has_parseable_nw1_blocks(outputs_word_file):
            print("\n[STOP] NW1 validation failed. Fix NW1 generation quality first.")
            return StageResult("failed", "NW1 validation found no usable blocks.")
        print("\n[WARN] NW1 validation failed, but usable blocks exist. Continuing.")
        warnings.append("NW1 validation exited non-zero with usable blocks.")

    qa_script = ROOT / "Tools" / "scripts" / "nw1_qa_review.py"
    if outputs_word_file.exists() and qa_script.exists():
        qa = run_cmd(nw1_qa_review.cmd, "NW1: QA review", log_fp=log_fp)
        if qa.returncode != 0 or "[WARN]" in (qa.stdout or ""):
            warnings.append("NW1 QA reported review issues.")

    detail = " ".join(warnings) if warnings else None
    return StageResult("completed_with_warnings" if warnings else "completed", detail)


def _run_nw2_prepare(log_fp: TextIO) -> StageResult:
    normalize = run_cmd(
        ["py", "-m", "mdproc", "process", "Outputs/01_words.md", "--output", "Outputs/02_words_fixed.md"],
        "NW2: Normalize words",
        log_fp=log_fp,
    )
    if normalize.returncode != 0:
        return StageResult("failed", "NW2 normalization failed.")
    extract = run_cmd(
        ["py", "-m", "mdproc", "words", "Outputs/02_words_fixed.md", "--output", "Outputs/03_word_list.md"],
        "NW2: Extract word list",
        log_fp=log_fp,
    )
    if extract.returncode != 0:
        return StageResult("failed", "NW2 word-list extraction failed.")
    return StageResult("completed", None)


def _write_empty_finalization_outputs() -> None:
    for relative_path in (
        "Outputs/04_see_also.md",
        "Outputs/05_see_also_fixed.md",
        "Outputs/06_words_final.md",
        "Outputs/06_words_final_fixed.md",
    ):
        (ROOT / relative_path).write_text("", encoding="utf-8", newline="\n")


def _run_nw3_nw4_finalize(log_fp: TextIO) -> StageResult:
    if count_word_list_entries(ROOT / "Outputs" / "03_word_list.md") == 0:
        _write_empty_finalization_outputs()
        return StageResult("completed", None)

    query = run_cmd(
        [sys.executable, str(SCRIPTS / "generate_requirement3_notebooklm.py")],
        "NW3: Query NotebookLM (stdio) and generate Outputs/04_see_also.md",
        log_fp=log_fp,
    )
    if query.returncode != 0:
        error_kind = classify_notebooklm_error((query.stdout or "") + "\n" + (query.stderr or ""))
        if error_kind != "auth":
            return StageResult("failed", "NW3 NotebookLM query failed.")
        print("[INFO] NotebookLM auth/session invalid. Attempting re-auth once...")
        if run_notebooklm_auth(cwd=ROOT) != 0:
            return StageResult("failed", "NotebookLM re-authentication failed.")
        query_retry = run_cmd(
            [sys.executable, str(SCRIPTS / "generate_requirement3_notebooklm.py")],
            "NW3: Query NotebookLM (retry after auth)",
            log_fp=log_fp,
        )
        if query_retry.returncode != 0:
            retry_kind = classify_notebooklm_error((query_retry.stdout or "") + "\n" + (query_retry.stderr or ""))
            if retry_kind == "auth":
                print("[STOP] NotebookLM auth/session still invalid after re-auth.")
            elif retry_kind == "network":
                print("[STOP] NotebookLM retry failed due network/session bootstrap issues.")
            return StageResult("failed", "NW3 NotebookLM retry failed.")

    preprocess = run_cmd(
        ["py", "-m", "mdproc", "preprocess", "Outputs/04_see_also.md", "--output", "Outputs/05_see_also_fixed.md"],
        "NW3: Preprocess see_also",
        log_fp=log_fp,
    )
    if preprocess.returncode != 0:
        return StageResult("failed", "NW3 see_also preprocessing failed.")
    merge = run_cmd(
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
    if merge.returncode != 0:
        return StageResult("failed", "NW3 see_also merge failed.")

    normalize = run_cmd(
        [sys.executable, str(SCRIPTS / "process_requirement4.py")],
        "NW4: Normalize see_also references",
        log_fp=log_fp,
    )
    if normalize.returncode != 0:
        return StageResult("failed", "NW4 normalization failed.")
    validate = run_cmd(
        [sys.executable, str(SCRIPTS / "validate_requirement4.py")],
        "NW4: Deep validation (authoritative)",
        log_fp=log_fp,
    )
    if validate.returncode != 0:
        recovery_script = SCRIPTS / "recover_missing_seealso.py"
        if not recovery_script.exists():
            return StageResult("failed", "NW4 validation failed and recovery script is missing.")
        print("[INFO] NW4 validation failed. Attempting automatic recovery via recover_missing_seealso.py ...")
        recovery = run_cmd(
            [sys.executable, str(recovery_script)],
            "NW4: Recovery (recover_missing_seealso.py)",
            log_fp=log_fp,
        )
        if recovery.returncode != 0:
            return StageResult("failed", "NW4 automatic recovery failed.")
        normalize_retry = run_cmd(
            [sys.executable, str(SCRIPTS / "process_requirement4.py")],
            "NW4: Normalize see_also references (post-recovery)",
            log_fp=log_fp,
        )
        if normalize_retry.returncode != 0:
            return StageResult("failed", "NW4 post-recovery normalization failed.")
        validate_retry = run_cmd(
            [sys.executable, str(SCRIPTS / "validate_requirement4.py")],
            "NW4: Deep validation (post-recovery)",
            log_fp=log_fp,
        )
        if validate_retry.returncode != 0:
            return StageResult("failed", "NW4 post-recovery validation failed.")

    authenticity = run_cmd(
        [sys.executable, str(SCRIPTS / "validate_see_also_authenticity.py"), "--input", "Outputs/04_see_also.md"],
        "NW3/NW4: Authenticity validation",
        log_fp=log_fp,
    )
    if authenticity.returncode != 0:
        print("\n[WARN] Authenticity check flagged issues. Please verify NotebookLM source quality.")
        return StageResult("completed_with_warnings", "NW3/NW4 authenticity validation reported issues.")
    return StageResult("completed", None)


def build_stages() -> list[Stage]:
    return [
        Stage(
            stage_id="nw1_prepare",
            dependencies=(),
            input_paths=(
                Path("Inputs/Word List (DE).md"),
                Path("Prompt/nw1_enrich_system.txt"),
                Path("Prompt/nw1_enrich_instructions.md"),
                Path("Prompt/nw1_qa_system.txt"),
                Path("Prompt/nw1_qa_instructions.md"),
                Path("configs/runtime.toml"),
            ),
            output_paths=(Path("Outputs/01_words.md"), Path("Outputs/reports/nw1_qa_latest.json")),
            definition_paths=(
                Path("Tools/scripts/process_requirement1.py"),
                Path("Tools/scripts/validate_word_list.py"),
                Path("Tools/scripts/nw1_qa_review.py"),
                Path("Tools/src/gnw_pipeline/nw1_steps.py"),
            ),
            completion_policy="usable_output",
            action=_run_nw1_prepare,
        ),
        Stage(
            stage_id="nw2_prepare",
            dependencies=("nw1_prepare",),
            input_paths=(Path("Outputs/01_words.md"), Path("Tools/src/mdproc")),
            output_paths=(Path("Outputs/02_words_fixed.md"), Path("Outputs/03_word_list.md")),
            definition_paths=(Path("Tools/src/mdproc"),),
            completion_policy="success",
            action=_run_nw2_prepare,
        ),
        Stage(
            stage_id="nw3_nw4_finalize",
            dependencies=("nw2_prepare",),
            input_paths=(
                Path("Outputs/02_words_fixed.md"),
                Path("Outputs/03_word_list.md"),
                Path("Prompt/nw3_notebooklm_query.md"),
                Path("configs/runtime.toml"),
            ),
            output_paths=(
                Path("Outputs/04_see_also.md"),
                Path("Outputs/05_see_also_fixed.md"),
                Path("Outputs/06_words_final.md"),
                Path("Outputs/06_words_final_fixed.md"),
            ),
            definition_paths=(
                Path("Tools/scripts/generate_requirement3_notebooklm.py"),
                Path("Tools/scripts/process_requirement4.py"),
                Path("Tools/scripts/validate_requirement4.py"),
                Path("Tools/scripts/recover_missing_seealso.py"),
                Path("Tools/scripts/validate_see_also_authenticity.py"),
                Path("Tools/src/mdproc"),
                Path("Tools/src/gnw_pipeline/notebooklm_runtime.py"),
            ),
            completion_policy="warning",
            action=_run_nw3_nw4_finalize,
        ),
    ]


def _write_success_summary(log_path: Path, reports_dir: Path) -> None:
    run_id = compute_run_id()
    is_empty = count_word_list_entries(ROOT / "Outputs" / "03_word_list.md") == 0
    summary: dict[str, object] = {
        "timestamp_utc": _utc_now_iso(),
        "run_id": run_id,
        "hashes": compute_prompt_hashes(),
        "outputs": {
            "final_markdown": str(ROOT / "Outputs" / "06_words_final_fixed.md"),
            "log": str(log_path),
        },
        "status": "ok_empty" if is_empty else "ok",
    }
    if is_empty:
        summary["note"] = "No resolved NW1 entries; pipeline completed with empty final outputs."
    run_latest = reports_dir / "run_latest.json"
    run_latest.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    runs_jsonl = reports_dir / "runs.jsonl"
    existing_run_ids: set[str] = set()
    if runs_jsonl.exists():
        for line in runs_jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and isinstance(record.get("run_id"), str):
                existing_run_ids.add(record["run_id"])
    if run_id not in existing_run_ids:
        with runs_jsonl.open("a", encoding="utf-8", newline="\n") as fp:
            fp.write(json.dumps(summary, ensure_ascii=False) + "\n")


def run_pipeline(*, resume: bool = False) -> int:
    logs_dir = ROOT / "Outputs" / "logs"
    reports_dir = ROOT / "Outputs" / "reports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    state_path = reports_dir / "pipeline_state.json"
    lock_path = reports_dir / "pipeline_state.lock"
    stages = build_stages()

    try:
        with pipeline_lock(lock_path):
            if resume and state_path.exists():
                state = _load_state(state_path)
            else:
                state = _initial_state(stages)
            records = _records_for(state, stages)
            _write_state(state_path, state)

            log_path = logs_dir / "run_latest.log"
            with log_path.open("w", encoding="utf-8", newline="\n") as log_fp:
                log_fp.write(f"[{_utc_now_iso()}] resume={str(resume).lower()}\n")
                clear_proxy_env()
                log_fp.write(f"[{_utc_now_iso()}] proxy_env_cleared=true\n")
                log_fp.flush()
                rerun_stage_ids: set[str] = set()

                for stage in stages:
                    record = records[stage.stage_id]
                    if resume and _is_reusable(stage, record, records, rerun_stage_ids):
                        print(f"[SKIP] {stage.stage_id}: reusable checkpoint")
                        log_fp.write(f"[{_utc_now_iso()}] [SKIP] {stage.stage_id}: reusable checkpoint\n")
                        log_fp.flush()
                        continue

                    rerun_stage_ids.add(stage.stage_id)
                    record.update(
                        {
                            "status": "running",
                            "definition_fingerprint": _definition_fingerprint(stage),
                            "input_fingerprint": _input_fingerprint(stage, records),
                            "output_fingerprints": None,
                            "started_at_utc": _utc_now_iso(),
                            "finished_at_utc": None,
                            "exit_code": None,
                            "detail": None,
                        }
                    )
                    _write_state(state_path, state)
                    try:
                        result = stage.action(log_fp)
                    except Exception as exc:
                        result = StageResult("failed", f"{stage.stage_id} raised {type(exc).__name__}.")

                    output_fingerprints = _output_fingerprints(stage)
                    if result.status in COMPLETED_STATUSES and output_fingerprints is None:
                        result = StageResult("failed", f"{stage.stage_id} did not produce all declared outputs.")

                    record.update(
                        {
                            "status": result.status,
                            "output_fingerprints": output_fingerprints if result.status in COMPLETED_STATUSES else None,
                            "finished_at_utc": _utc_now_iso(),
                            "exit_code": 0 if result.status in COMPLETED_STATUSES else 1,
                            "detail": result.detail,
                        }
                    )
                    _write_state(state_path, state)
                    if result.status == "failed":
                        print(f"\n[FAIL] {stage.stage_id}: {result.detail or 'stage failed'}")
                        return 1

            _write_success_summary(log_path, reports_dir)
            print("\n[OK] Pipeline completed through NW4.")
            return 0
    except PipelineLockError as exc:
        print(f"[FAIL] {exc}")
        return 2
    except PipelineStateError as exc:
        print(f"[FAIL] {exc}")
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run German_NewWords pipeline.")
    parser.add_argument("--resume", action="store_true", help="Resume reusable logical stages from pipeline_state.json.")
    args = parser.parse_args(argv)
    return run_pipeline(resume=args.resume)


if __name__ == "__main__":
    raise SystemExit(main())
