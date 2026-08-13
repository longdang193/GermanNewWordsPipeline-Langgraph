---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: pipeline-stage-resume
parent_spec: docs/superpowers/specs/2026-08-07-10-50-pipeline-stage-resume-spec.md
targets:
  - Tools/scripts/run_full_pipeline.py
  - Tools/src/gnw/__main__.py
  - Tools/src/gnw/ui.py
  - Tools/tests/test_run_full_pipeline.py
  - Tools/tests/test_gnw_cli.py
  - Tools/tests/test_gnw_ui.py
  - Tools/scripts/build_windows_exe.ps1
  - README.md
  - Tools/scripts/README.md
  - dist/GermanNewWords/GermanNewWords.exe
related_features:
  - pipeline-orchestration
related_stages:
  - NW1
  - NW2
  - NW3
  - NW4
---

# Plan: Uniform pipeline-stage resume

## Note (canonical template gap)

Repo lacks `docs/operating_system/templates/implementation-plan-template.md` and `docs/operating_system/tooling/code-intelligence-tools.md`. This plan follows existing repository plan shape and approved specification.

## Goal

Implement explicit fresh and resume execution through one script-runner checkpoint contract. Preserve current outputs, warnings, NotebookLM retries, and Windows distribution behavior while removing public `gnw` dependence on optional LangGraph execution.

## Scope

- One `Outputs/reports/pipeline_state.json` current-run checkpoint.
- Three logical stages: `nw1_prepare`, `nw2_prepare`, `nw3_nw4_finalize`.
- Explicit `--resume` for script runner and `gnw run`.
- Explicit fresh/resume UI actions forwarding same runner intent.
- Focused runner, CLI, UI, documentation, and packaged-exe proof.

Excluded:

- New dependencies, database, queue, scheduler, per-stage state files, or parallel execution.
- Changes to NW1–NW4 domain rules, prompt content, NotebookLM protocol, or generated Markdown format.
- Any resume implementation in `gnw_pipeline.langgraph_app`.

## Execution Approach

- Approach: inline sequential.
- Shared-write owner: one executor. `Tools/scripts/run_full_pipeline.py` owns checkpoint semantics; wrappers only forward `resume` boolean.
- Required skills:
  - `skill-test-driven-development`
  - `skill-backend-verification`
  - `skill-code-standards`
- No worktree or parallel lane. Core runner, wrappers, tests, docs, and binary are serial dependencies.

## Task 1: Add checkpointed logical-stage runner

**Purpose:**
Make `Tools/scripts/run_full_pipeline.py` own all resume state and execute every logical stage through one registry and reuse rule.

**Specification Coverage:**
Sections 4.1–4.6, 4.8–4.9, 5–6; acceptance criteria for failed NW3, invalidation, interruption, warnings, corrupt state, and concurrent invocation.

**Required Skills:**
`skill-test-driven-development`, `skill-backend-verification`, `skill-code-standards`.

**Files And Symbols:**
- `Tools/scripts/run_full_pipeline.py`: `run_pipeline`, `run_cmd`, new local checkpoint helpers, logical-stage registry, and script CLI entrypoint.
- `Tools/tests/test_run_full_pipeline.py`: existing NW1 continuation tests plus new resume tests.

**Dependencies:**
None.

**Steps:**
1. Add RED tests first for: fresh state creation; successful resume skipping all reusable stages; failed `nw3_nw4_finalize` resuming without NW1/NW2 calls; changed finalization input rerunning only finalization; `running` stage rerun; reusable warning stage; corrupt JSON fail-before-command; held exclusive lock fail-before-command; empty NW2 word list producing final empty outputs through finalization stage.
2. Prove lock contention with a spawned child process holding the native lock, not two lock attempts in one Python process. This verifies Windows cross-process ownership and release behavior.
3. Keep all new implementation local to `run_full_pipeline.py`; use standard-library JSON, SHA-256, temporary-file replacement, and native Windows-compatible exclusive file locking. Add no package.
4. Give every logical-stage action one return contract: terminal status (`completed`, `completed_with_warnings`, or `failed`) plus sanitized detail. Only generic runner code writes manifest state; actions must not write checkpoint state directly.
5. Replace current command-level linear orchestration with three logical stage actions:
   - `nw1_prepare`: existing generation, usable-block validation continuation, and QA review.
   - `nw2_prepare`: existing normalization and word-list extraction.
   - `nw3_nw4_finalize`: existing NW3 auth retry, NW3 preprocessing/merge, NW4 normalization/validation/recovery loop, and authenticity check.
6. Define one registry containing each stage ID, dependency IDs, input paths, output paths, definition-source paths, completion policy, and action callback. Keep retries and recovery inside action callbacks; do not checkpoint command substeps.
7. Use this explicit state mapping:
   - `nw1_prepare`: inputs `Inputs/Word List (DE).md`, NW1 prompts, `configs/runtime.toml`, and NW1 script sources; outputs `Outputs/01_words.md` and `Outputs/reports/nw1_qa_latest.json`.
   - `nw2_prepare`: inputs `Outputs/01_words.md` and `Tools/src/mdproc`; outputs `Outputs/02_words_fixed.md` and `Outputs/03_word_list.md`.
   - `nw3_nw4_finalize`: inputs `Outputs/02_words_fixed.md`, `Outputs/03_word_list.md`, `Prompt/nw3_notebooklm_query.md`, `configs/runtime.toml`, and NW3/NW4 script sources; outputs `Outputs/04_see_also.md`, `Outputs/05_see_also_fixed.md`, `Outputs/06_words_final.md`, and `Outputs/06_words_final_fixed.md`.
8. Fingerprint declared inputs, dependencies, command configuration, completion policy, and listed direct repo-owned source/config files per stage. Treat a missing declared file as deterministic fingerprint input. Do not use one whole-pipeline fingerprint.
9. Persist `running` before calling each stage. On success persist `completed`; preserve current usable-block and warning outcomes as `completed_with_warnings`; on blocking failure persist `failed` with sanitized process detail and return non-zero. Never serialize credentials, environment, or NotebookLM session data.
10. Resume evaluates registry entries using one reusable-stage predicate. It skips only matching completed/warning stages with matching definition/input/output fingerprints and reusable dependencies. Stale or `running` stages execute; every dependent stage is re-evaluated afterward.
11. Move deletion of `Outputs/01_words.md` into `nw1_prepare` action so skipped NW1 never deletes its output. Preserve existing fresh-run behavior by running `nw1_prepare` on every non-resume invocation.
12. Add script `--resume` parsing while preserving no-argument fresh behavior. Keep `run_pipeline(resume=False)` callable by existing tests.
13. Keep `run_latest.json` and `runs.jsonl` success reporting behavior. Do not treat either as checkpoint input.

**Verification:**
```powershell
cd Tools
py -m pytest -q tests/test_run_full_pipeline.py
```

**Exit Criteria:**
- New tests fail before implementation and pass after it.
- State file is sole current resumable-state source.
- All specified state, failure, warning, invalidation, and lock tests pass.
- Existing NW1 continuation tests still pass.

## Task 2: Forward explicit intent through CLI and Windows UI

**Purpose:**
Expose fresh and resume actions without a second resume implementation.

**Specification Coverage:**
Sections 4.7 and 6; distribution-intent acceptance criterion.

**Required Skills:**
`skill-test-driven-development`, `skill-code-standards`.

**Files And Symbols:**
- `Tools/src/gnw/__main__.py`: `cmd_run`, `build_parser`.
- `Tools/src/gnw/ui.py`: `run_pipeline`, `run_ui` menu and result labels.
- `Tools/tests/test_gnw_cli.py`: CLI forwarding tests.
- `Tools/tests/test_gnw_ui.py`: new focused menu/runner forwarding tests.

**Dependencies:**
Task 1.

**Steps:**
1. Add RED CLI tests proving `gnw run` launches script runner without `--resume`, `gnw run --resume` launches it with `--resume`, and both paths use script runner even when optional LangGraph import succeeds.
2. Add RED UI tests proving `run_pipeline(root, resume=False)` and `run_pipeline(root, resume=True)` forward only that boolean to `run_full_pipeline.py`; menu fresh and resume choices call matching helper arguments.
3. Remove public `cmd_run` LangGraph selection. Always invoke `Tools/scripts/run_full_pipeline.py`; preserve root detection, proxy clearing, frozen-exe Python launcher, and missing-launcher failure behavior.
4. Add `--resume` boolean to `gnw run` parser. Append it only when true.
5. Change UI helper to accept keyword-only `resume: bool = False`, append `--resume` only when true, and rename/add menu options to `Run pipeline (fresh)` and `Resume last run`.
6. Keep UI checkpoint-agnostic. It must not read `pipeline_state.json`, infer stage validity, or auto-select resume.

**Verification:**
```powershell
cd Tools
py -m pytest -q tests/test_gnw_cli.py tests/test_gnw_ui.py
```

**Exit Criteria:**
- New forwarding tests fail before implementation and pass after it.
- CLI/UI expose explicit modes only.
- `gnw run` cannot select optional LangGraph path.

## Task 3: Document and package distribution surface

**Purpose:**
Publish one operator workflow and rebuild tracked executable from canonical sources.

**Specification Coverage:**
Sections 4.6–4.7, 6, and distribution-intent acceptance criterion.

**Required Skills:**
`skill-code-standards`.

**Files And Symbols:**
- `README.md`: Fast start, pipeline, and recovery instructions.
- `Tools/scripts/README.md`: script runner usage.
- `dist/GermanNewWords/GermanNewWords.exe`: rebuilt tracked artifact.

**Dependencies:**
Tasks 1–2.

**Steps:**
1. Document fresh `py Tools/scripts/run_full_pipeline.py`, resume `py Tools/scripts/run_full_pipeline.py --resume`, fresh `gnw run`, and resume `gnw run --resume`.
2. Document UI actions and state that executable never auto-resumes; `Resume last run` forwards one explicit resume request and may start fresh when no state exists.
3. State recovery boundary: corrupt `pipeline_state.json` stops resume; remove that file intentionally to start fresh. Do not instruct users to edit generated outputs or manually run downstream scripts.
4. Rebuild tracked executable with existing command:
   ```powershell
   pwsh -NoProfile -ExecutionPolicy Bypass -File Tools/scripts/build_windows_exe.ps1
   ```
5. Make build script fail when PyInstaller returns non-zero; never print successful-build output for a stale executable.
5. Smoke-test parser surface without running pipeline:
   ```powershell
   dist/GermanNewWords/GermanNewWords.exe --root . run --help
   ```

**Verification:**
- Documentation commands match parser behavior.
- Build command exits zero.
- Packaged executable help exits zero and displays `--resume`.

**Exit Criteria:**
- Root and script documentation name only supported fresh/resume workflows.
- Tracked executable contains current CLI surface.

## Task 4: Run final direct proof and reconcile spec

**Purpose:**
Prove current state, failure recovery, interface forwarding, and packaged contract after all edits.

**Specification Coverage:**
All acceptance criteria and completion criteria.

**Required Skills:**
`skill-backend-verification`, `skill-verification-before-completion`.

**Files And Symbols:**
- `Tools/scripts/run_full_pipeline.py`
- `Tools/src/gnw/__main__.py`
- `Tools/src/gnw/ui.py`
- `Tools/tests/test_run_full_pipeline.py`
- `Tools/tests/test_gnw_cli.py`
- `Tools/tests/test_gnw_ui.py`
- `README.md`
- `Tools/scripts/README.md`
- `dist/GermanNewWords/GermanNewWords.exe`

**Dependencies:**
Tasks 1–3.

**Steps:**
1. Run focused runner and distribution-interface tests together.
2. Run full Tools test suite once after focused proof passes.
3. Inspect one test-created state manifest for required schema, no secrets, terminal stage outcomes, and fingerprints.
4. Run `git diff --check`; review changed paths against this plan; do not modify unrelated outputs.
5. Record direct boundary evidence: fresh run state creation, failed finalization resume, corrupt-state refusal, lock refusal, CLI/UI intent forwarding, and executable `--resume` help.

**Verification:**
```powershell
cd Tools
py -m pytest -q tests/test_run_full_pipeline.py tests/test_gnw_cli.py tests/test_gnw_ui.py
py -m pytest -q
cd ..
git diff --check
```

**Exit Criteria:**
- Focused and full tests pass.
- Direct state-file behavior proves success, important failures, final state, and idempotent resume disposition.
- Docs and rebuilt executable expose same explicit interface.
- No remaining specification acceptance criterion lacks evidence.

## Rollback

- Before release, restore only changed source, documentation, test, and tracked executable files from Git if checkpoint behavior regresses.
- Remove `Outputs/reports/pipeline_state.json` to discard runtime state. Do not delete generated Markdown outputs as rollback.
