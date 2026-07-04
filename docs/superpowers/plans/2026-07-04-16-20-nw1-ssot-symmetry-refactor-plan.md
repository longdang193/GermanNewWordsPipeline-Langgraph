---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: nw1-ssot-symmetry-refactor
parent_thread: current-thread
parent_spec: docs/superpowers/specs/2026-07-04-16-05-nw1-ssot-symmetry-refactor-spec.md
targets:
  - docs/superpowers/specs/2026-07-04-16-05-nw1-ssot-symmetry-refactor-spec.md
  - Tools/scripts/process_requirement1.py
  - Tools/scripts/validate_word_list.py
  - Tools/scripts/nw1_qa_review.py
  - Tools/scripts/run_full_pipeline.py
  - Tools/src/gnw_pipeline/nw1_qa.py
  - Tools/src/gnw_pipeline/nw1_quality_rules.py
  - Tools/src/gnw_pipeline/nw1_steps.py
  - Tools/src/gnw_pipeline/nw1_llm_qa.py
  - Tools/src/gnw_pipeline/nw1_llm_enrich.py
  - Tools/src/gnw_pipeline/llm_runtime.py
  - Tools/src/gnw_pipeline/langgraph_app.py
  - Tools/tests/test_process_requirement1_failure_contract.py
  - Tools/tests/test_validate_word_list_script.py
  - Tools/tests/test_run_full_pipeline.py
  - Tools/README.md
  - Tools/scripts/README.md
related_features:
  - nw1-generation
  - nw1-qa
  - nw1-orchestration
related_stages:
  - NW1
---

# Note (canonical template gap)

Repo paths required by `skill-writing-plans` are missing locally. This plan follows current repo frontmatter and section shape.

# Goal

Implement the NW1 SSOT/symmetry refactor with smallest safe sequence: define one authoritative per-input result contract, align validator and QA around that contract, centralize duplicated NW1 content-quality heuristics, remove stale unresolved-comment behavior, and stop NW1 orchestration drift from growing further.

# Scope

- In scope: NW1 only.
- In scope files: generator, validator, QA review, runner, LangGraph NW1 step wiring, typed NW1 QA contract, shared NW1 helper surfaces, focused tests, and NW1-facing docs.
- In scope behavior:
  - explicit `input-term result` artifact
  - explicit `written block QA row` artifact
  - validator exit truth table
  - current-tail unresolved contract
  - NW1 CLI/LangGraph parity for generate/validate/QA/continuation only
- Out of scope:
  - NW3 query-script parity
  - NW2–NW4 schema changes
  - prompt-policy changes beyond naming/contract alignment
  - new repair loops or HITL workflow
  - new persistence layer

# Diagnosis

- NW1 unresolved/blocker truth currently lives in transient generator dicts, not a shipped SSOT artifact.
- Validator still carries legacy unresolved-comment behavior and stale tests for `UNRESOLVED_JSON`.
- Generation-time acceptance still stringifies hard-fail issues and reparses them later.
- Generic-content heuristics are duplicated across generator and validator.
- CLI runner and LangGraph have NW1 orchestration drift, and LangGraph still diverges more broadly.
- One validator test file is already failing under current contract, so baseline drift is proven.

# Resolution Contract

1. NW1 must publish one report artifact at `Outputs/reports/nw1_qa_latest.json`.
2. That artifact must contain at minimum these top-level keys:
   - `results`
   - `issue_rows`
   - `env`
   - `summary`
3. `results` is one row per extracted NW1 source entry and is the only authoritative machine-readable source for:
   - `input_index`
   - `term`
   - `resolution_status`
   - `origin_reason_code`
   - `final_blocker_code`
   - optional `final_blocker_codes`
4. `issue_rows` is one row per parseable written block with issues and remains additive to current block QA fields.
5. `Outputs/01_words.md` remains content artifact only; no per-block unresolved reason comments return.
6. `input_index` is the stable identity key and must equal 0-based position in extracted NW1 source list before dedupe.
7. Duplicate extracted entries must still be represented deterministically in `results` with explicit non-write disposition rather than disappearing silently.
8. Validator must not depend on legacy unresolved comments.
9. Validator exit truth table is fixed:
   - structural invalidity -> non-zero
   - omitted present -> non-zero
   - unresolved_part without omitted -> zero
   - clean-only -> zero
10. `mdproc` stays structural-only; NW1 semantic/content heuristics live in `Tools/src/gnw_pipeline/nw1_quality_rules.py`.
11. CLI runner and LangGraph must share NW1 generate/validate/QA/continuation semantics through one shared NW1 step contract owned by `Tools/src/gnw_pipeline/nw1_steps.py`.
12. NW3 command parity is explicitly deferred.

# Key Deliverables

1. One typed NW1 report contract in `Tools/src/gnw_pipeline/nw1_qa.py` that separates `results` from `issue_rows` inside `Outputs/reports/nw1_qa_latest.json`.
2. One `process_requirement1.py` flow that emits typed status data instead of string-roundtrip blocker parsing.
3. One validator that consumes current-tail plus `results`, not legacy unresolved comments.
4. One shared NW1 generic-content rule source in `Tools/src/gnw_pipeline/nw1_quality_rules.py` used by generator and validator.
5. One NW1-only orchestration parity layer in `Tools/src/gnw_pipeline/nw1_steps.py` consumed by `run_full_pipeline.py` and `langgraph_app.py`.
6. One cleanup of stale tests/docs/wrappers tied to obsolete unresolved-comment behavior.
7. One focused regression suite proving artifact grain, truth-table behavior, count invariants, duplicate handling, and NW1 runner parity.

# Task Breakdown

## Task 0 — Freeze current contract with focused baseline checks

**Files**
- `Tools/tests/test_process_requirement1_failure_contract.py`
- `Tools/tests/test_validate_word_list_script.py`
- `Tools/tests/test_run_full_pipeline.py`

**Work**
- Record current intended NW1 behavior with focused tests before refactor.
- Keep existing passing NW1 failure-contract and runner tests as guardrails.
- Mark stale validator JSON-comment tests for rewrite in later task, not silent deletion.
- Verify and note current failing validator test as expected baseline drift.
- This task is evidence-only, not a full-green gate.

**Verification**
- `py -m pytest Tools/tests/test_process_requirement1_failure_contract.py -q`
- `py -m pytest Tools/tests/test_run_full_pipeline.py -q`
- `py -m pytest Tools/tests/test_validate_word_list_script.py -q` shows exactly current stale-contract failures before patching.

## Task 1 — Introduce typed `results` and `issue_rows` SSOT (`R1`)

**Files**
- `Tools/src/gnw_pipeline/nw1_qa.py`
- `Tools/scripts/process_requirement1.py`
- `Tools/scripts/nw1_qa_review.py`

**Work**
- Add one typed `input-term result` contract in `nw1_qa.py` with explicit stable identity key `input_index`.
- Extend report payload builder so `Outputs/reports/nw1_qa_latest.json` carries:
  - `results`
  - `issue_rows`
  - `env`
  - `summary`
- Keep current `issue_rows` block fields additive.
- Make `process_requirement1.py` produce or preserve per-input result data for clean/unresolved_part/omitted/duplicate outcomes.
- Ensure omitted terms appear only in `results`, never as fake block rows.
- Keep output block writing behavior unchanged.

**Verification**
- One focused integration test proves one omitted item appears in `results` with `resolution_status=omitted` and does not appear in `issue_rows`.
- One focused test proves unresolved-part item appears in both places when it is a written block with issues.
- One focused test proves clean item appears in `results` and is absent from `issue_rows` when no issues exist.
- One focused test proves duplicate extracted item gets deterministic row treatment and does not corrupt count invariants.

## Task 2 — Remove string-roundtrip blocker plumbing (`R3`)

**Files**
- `Tools/scripts/process_requirement1.py`
- `Tools/src/gnw_pipeline/nw1_qa.py`
- `Tools/tests/test_process_requirement1_failure_contract.py`

**Work**
- Replace `validate_entry_quality() -> list[str]`-style blocker plumbing with typed issue/result use.
- Preserve current hard-fail/soft-review semantics and current issue codes.
- Reuse typed issue codes directly when setting `final_blocker_code` and `final_blocker_codes`.
- Do not introduce new class hierarchy beyond smallest dataclass/TypedDict needed.

**Verification**
- One focused test proves no string roundtrip is needed to recover `target_not_realized`.
- Existing failed-repair/unresolved-tail tests still pass.

## Task 3 — Centralize generic-content heuristics (`R4`)

**Files**
- `Tools/src/gnw_pipeline/nw1_quality_rules.py`
- `Tools/scripts/process_requirement1.py`
- `Tools/scripts/validate_word_list.py`
- focused NW1 tests

**Work**
- Extract duplicated generic-content markers/patterns into one NW1-owned helper/constants surface under `Tools/src/gnw_pipeline/nw1_quality_rules.py`.
- Make generator-time and validator-time checks import same source.
- Keep `mdproc` out of semantic-rule ownership.
- Rewrite stale duplicate local lists in both call sites to thin consumers.

**Verification**
- One shared fixture triggers same rejection in both generator-time and validator-time paths.
- Source grep shows one owner of generic-content markers.

## Task 4 — Replace legacy unresolved-comment validator logic (`R2`)

**Files**
- `Tools/scripts/validate_word_list.py`
- `Tools/tests/test_validate_word_list_script.py`
- `Tools/README.md`
- `Tools/scripts/README.md`

**Work**
- Keep `validate_word_list.py` as single validator.
- Remove validator dependence on `UNRESOLVED_JSON` and `UNRESOLVED` comments.
- Make validator reason about unresolved state using current output shape plus `results` artifact from `Outputs/reports/nw1_qa_latest.json`.
- Keep validator structural/block checks intact.
- Rewrite stale validator tests to current-tail and `results` contract.
- Update docs that still mention JSON unresolved comments.

**Verification**
- `py -m pytest Tools/tests/test_validate_word_list_script.py -q` passes.
- Validator truth table is covered by tests for:
  - clean-only
  - unresolved_part-only
  - omitted-present
  - structural-invalid

## Task 5 — Enforce validator truth table explicitly

**Files**
- `Tools/scripts/validate_word_list.py`
- focused validator tests

**Work**
- Make exit semantics explicit and testable.
- Keep unresolved_part non-fatal when no omitted or structural invalidity exists.
- Keep omitted and structural invalidity fatal.
- Keep output messages aligned with new semantics.

**Verification**
- One test per truth-table branch.
- Validator messages match actual exit semantics.

## Task 6 — Unify NW1 CLI and LangGraph parity (`R5`, bounded)

**Files**
- `Tools/src/gnw_pipeline/nw1_steps.py`
- `Tools/scripts/run_full_pipeline.py`
- `Tools/src/gnw_pipeline/langgraph_app.py`
- `Tools/tests/test_run_full_pipeline.py`
- one parity-focused test for LangGraph step contract

**Work**
- Introduce one small shared NW1 step contract in `Tools/src/gnw_pipeline/nw1_steps.py`.
- Align only NW1 generate/validate/QA steps and parseable-block continuation logic.
- Do not normalize NW3 query script choice in this task.
- Ensure LangGraph does not silently lag NW1 continuation semantics.

**Verification**
- One parity test asserts CLI runner and LangGraph share:
  - same NW1 generate command
  - same NW1 validate command
  - same NW1 QA command
  - same continuation rule when parseable blocks exist

## Task 7 — Remove stale wrappers and leftovers (`R6` + `R7`)

**Files**
- `Tools/scripts/nw1_qa_review.py`
- `Tools/src/gnw_pipeline/nw1_qa.py`
- `Tools/src/gnw_pipeline/nw1_llm_qa.py`
- `Tools/src/gnw_pipeline/nw1_llm_enrich.py`
- docs/tests touched by obsolete assumptions

**Work**
- Make QA review use shared parser path instead of bespoke block parsing where possible.
- Remove or justify dead wrappers/constants such as obsolete unresolved-comment assumptions and unused prompt/runtime leftovers.
- In `nw1_llm_qa.py`, limit cleanup to dead constants/wrappers and do not change live prompt behavior unless tests prove no active consumer.
- Keep only active compatibility helpers with callers and tests.

**Verification**
- Source grep shows obsolete unresolved JSON assumptions removed from active NW1 path.
- Any retained compatibility wrapper has at least one active caller and one test or explicit justification.

## Task 8 — Final NW1 refactor verification

**Files**
- no new code target; verification only

**Work**
- Run focused NW1 suites.
- Inspect generated report shape and written output shape together.
- Assert final JSON artifact shape for `Outputs/reports/nw1_qa_latest.json`.
- Optionally run one live NW1 or full pipeline smoke if extra confidence is needed.

**Verification**
- `py -m pytest Tools/tests/test_process_requirement1_failure_contract.py -q`
- `py -m pytest Tools/tests/test_validate_word_list_script.py -q`
- `py -m pytest Tools/tests/test_run_full_pipeline.py -q`
- if touched, targeted tests for shared helper and QA review parsing
- one focused test asserts top-level JSON artifact keys and required row fields
- optional smoke: `py Tools/scripts/run_full_pipeline.py`

# Dependency Ordering

1. Task 0 first — freeze intended behavior and expose stale tests.
2. Task 1 before Task 4 — validator cannot consume `results` until `results` exist.
3. Task 2 before or with Task 1 finalization — typed blocker plumbing should reuse new result contract.
4. Task 3 before Task 4 finalization — validator and generator should switch to shared heuristics together.
5. Task 5 after Task 4 — truth table belongs on top of new validator inputs.
6. Task 6 after Tasks 1 and 5 — orchestration parity needs settled result/validator semantics.
7. Task 7 after active consumers are migrated.
8. Task 8 last.

# Rollback / Containment

- Keep refactor additive where possible until tests pass:
  - add `results` before removing old transient paths
  - add shared heuristic source before deleting duplicated lists
  - add shared NW1 step contract before deleting handwritten NW1 parity logic
- If validator refactor destabilizes CLI flow, preserve current `Outputs/01_words.md` write contract and temporarily gate new validator logic behind internal helper boundary, not user config.
- If LangGraph parity work expands beyond NW1, stop and split follow-on spec/plan for NW3 parity rather than widening this change.

# Validation Rules

- `results` and `issue_rows` must never be conflated.
- `input_index` must be stable per extracted source entry before dedupe and present on every `results` row.
- Omitted entries must appear in `results` and must not appear as fake block QA rows.
- Shared generic-content rule source must have one owner under `Tools/src/gnw_pipeline/nw1_quality_rules.py`.
- Validator must not read unresolved JSON comments after refactor.
- CLI and LangGraph parity in this plan is NW1-only.
- `Outputs/reports/nw1_qa_latest.json` is the sole report artifact for `results` and `issue_rows`.

# Best Lazy Implementation

- Add one small typed `results` dataclass/TypedDict next to existing NW1 QA types.
- Extend existing QA report JSON instead of inventing a second report file.
- Keep `validate_word_list.py` as single validator: structural checks plus `results` truth table.
- Add one tiny shared NW1 heuristic module instead of moving semantics into `mdproc`.
- Share NW1 step metadata with one helper/list, not a framework.

# Verification

- Focused pytest commands from Task 8.
- One live smoke only if needed after focused tests pass.
- Optional final artifact check:
  - `Outputs/01_words.md`
  - `Outputs/reports/nw1_qa_latest.json`
  - `Outputs/reports/run_latest.json`

# Precondition Note

This plan assumes parent spec `docs/superpowers/specs/2026-07-04-16-05-nw1-ssot-symmetry-refactor-spec.md` is the approved source of truth. If artifact grain, validator ordering, or `R5` NW1-only scope changes again, patch spec first and then regenerate this plan.
