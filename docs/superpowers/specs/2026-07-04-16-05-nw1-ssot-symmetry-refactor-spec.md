---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: nw1-ssot-symmetry-refactor
parent_workstream: none
targets:
  - Tools/scripts/process_requirement1.py
  - Tools/scripts/validate_word_list.py
  - Tools/scripts/nw1_qa_review.py
  - Tools/scripts/run_full_pipeline.py
  - Tools/src/gnw_pipeline/nw1_qa.py
  - Tools/src/gnw_pipeline/nw1_llm_qa.py
  - Tools/src/gnw_pipeline/nw1_llm_enrich.py
  - Tools/src/gnw_pipeline/llm_runtime.py
  - Tools/src/gnw_pipeline/langgraph_app.py
  - Tools/tests/test_process_requirement1_failure_contract.py
  - Tools/tests/test_validate_word_list_script.py
  - Tools/tests/test_run_full_pipeline.py
  - Prompt/nw1_enrich_instructions.md
  - Prompt/nw1_qa_instructions.md
  - Tools/README.md
  - Tools/scripts/README.md
related_features:
  - nw1-generation
  - nw1-qa
  - nw1-orchestration
related_stages:
  - NW1
---

# Spec: NW1 SSOT, symmetry, and invariance refactor

## Note (canonical template gap)

Repo currently lacks canonical `docs/operating_system/...` template files referenced by skills. This spec follows required section set and existing repo spec shape.

## Triage

Layer: change  
Feature type: MODIFY  
Summary: remove NW1 contract drift across generation, validator, QA report, and orchestration by making unresolved state, QA rows, and NW1 step wiring source-of-truth driven  
Affected stages: NW1  
Affected features: nw1-generation, nw1-qa, nw1-orchestration  
Spec needed: yes  
Plan needed: yes

## 1) Goal

Refactor NW1 so equivalent concepts use one authoritative contract and equivalent flows behave the same.

Primary goals:
- make unresolved-entry status a real shipped SSOT artifact instead of transient dict data
- remove drift between generation-time acceptance, post-generation validation, and QA reporting
- align CLI and LangGraph NW1 orchestration so equivalent pipeline surfaces use equivalent step definitions and continuation rules
- remove stale legacy unresolved-comment behavior that no longer matches live output
- centralize duplicated NW1 content-quality heuristics that currently drift across generator and validator

This refactor is structural. It must preserve current intended external behavior:
- valid clean blocks stay in main body
- valid but unaccepted blocks stay under `## UNRESOLVED PART`
- structurally unusable entries remain omitted
- NW3/NW4 can continue when usable NW1 blocks exist

This spec uses three distinct grains and does not allow them to blur:
- `input-term result` = one row per extracted NW1 source entry, whether written or omitted
- `written block QA row` = one row per parseable written `SSTART...EEND` block that has one or more issues
- `output block` = one serialized block written to `Outputs/01_words.md`

`input-term result` is authoritative for `resolution_status` and blocker metadata.
`written block QA row` is authoritative for issue review on written blocks only.
`output block` is authoritative only for serialized learning content plus stable section placement.

## 2) Key Deliverables

1. One `input-term result` contract owned by `Tools/src/gnw_pipeline/nw1_qa.py`.
2. One `written block QA row` schema owned by `Tools/src/gnw_pipeline/nw1_qa.py`.
3. One validator contract that reads current NW1 output shape plus `input-term result` artifact, not legacy unresolved comments.
4. One shared generic-content rule source used by both generation-time and post-generation checks.
5. One unified NW1 orchestration model for CLI and LangGraph NW1 step order and NW1 continuation semantics only.
6. One cleanup pass removing obsolete tests, helpers, constants, and docs that still describe superseded unresolved-comment behavior.
7. One focused regression suite proving SSOT, symmetry, and invariance across NW1 surfaces.

## 3) Task/Wave Breakdown

### Wave A — Resolve status SSOT (`R1`)
- Add explicit NW1 resolution metadata to authoritative QA/report surfaces.
- Move `resolution_status`, `origin_reason_code`, and `final_blocker_code` out of transient-only generator dict flow.
- Make one shipped `input-term result` artifact the single machine-readable explanation surface for unresolved and omitted state.
- Keep `written block QA row` artifact scoped to written blocks only.

### Wave B — Remove legacy unresolved-comment contract (`R2`)
- Delete validator dependence on `UNRESOLVED_JSON` and `UNRESOLVED` comments.
- Replace stale comment-based unresolved detection with current-tail plus `input-term result` logic.
- Update tests and docs that still assert JSON unresolved comments.

### Wave C — Stop stringly-typed issue plumbing (`R3`)
- Replace `list[str]` issue passing in generation-time acceptance with typed issue/result structures.
- Keep `process_requirement1.py` as consumer of typed QA rules, not a parallel parser of stringified issue text.
- Preserve current hard-fail vs soft-review semantics.

### Wave D — Centralize generic-content heuristics (`R4`)
- Move duplicated generic-content markers/patterns into one shared helper or constants module.
- Make generator-time rejection and validator-time rejection consume same source.
- Keep behavior stable unless a targeted rule change is explicitly approved.

### Wave E — Unify orchestration surfaces (`R5`)
- Define one NW1 step manifest or equivalent shared command contract.
- Make `run_full_pipeline.py` and `langgraph_app.py` use same NW1 generate/validate/QA steps and same NW1 continuation gate.
- Do not change NW3 command selection in this spec. If NW3 script parity is still required after NW1 alignment, write separate spec/plan.

### Wave F — Remove stale surfaces (`R6`)
- Remove or update obsolete tests, wrappers, prompt constants, and docs that no longer match NW1 contract.
- Remove dead compatibility shims only after replacement contract is verified.

### Wave G — Remove duplicate block parsing (`R7`)
- Make block-to-entry parsing flow through one parser path.
- Keep QA review and generation-time QA consuming same entry extraction logic.

## 4) Design Decisions

### 4.1 Resolution status becomes first-class data

Normalization target:
- one `input-term result` contract must represent exactly one extracted source entry and carry:
  - `input_index`
  - `term`
  - `resolution_status = clean | unresolved_part | omitted`
  - `origin_reason_code`
  - `final_blocker_code`
  - optional `final_blocker_codes`
  - optional stable references to written block location when written
- this contract must be authoritative for machine-readable unresolved explanation

`input_index` is the stable row identity key.
`term` is display text, not sole identity.

One `written block QA row` contract must represent exactly one parseable written block and carry:
- `word`
- `word_inf`
- `start_line`
- `end_line`
- `issues`
- optional `input_index` backlink when available

Design rule:
- `Outputs/01_words.md` remains block artifact
- one NW1 report artifact may contain both `results` and `issue_rows`, but their grains must remain distinct
- no per-block reason comments are reintroduced into canonical NW1 output

### 4.2 Equivalent validation concepts must share one rule source

Equivalent concepts currently split across surfaces:
- de_1 QA hard-fail rules
- generic fallback-content detection
- unresolved-state detection
- block-to-entry parsing

Symmetry model:
- generator-time acceptance and post-generation validator must call shared rule sources
- QA review must not reimplement entry parsing if shared parser already exists
- validator must not invent obsolete unresolved semantics once result status exists

Ownership rule:
- semantic/content heuristics for NW1 live in one NW1-owned helper module under `Tools/src/gnw_pipeline/`
- `mdproc` remains structural/block-schema validator and does not become owner of NW1 semantic heuristics

### 4.3 Orchestration must be command-symmetric

CLI and LangGraph are equivalent NW1 pipeline entrypoints and should differ only by execution host, not by step semantics.

Required alignment:
- same NW1 generate command
- same NW1 validate command
- same NW1 QA command
- same NW1 partial-write continuation rule

Out of scope for this spec:
- same NW3 query command choice
- broader NW3/NW4 orchestration normalization beyond what is necessary to keep NW1 parity truthful

Ordering rule:
- if validator consumes only block-structural rules, it may stay before QA review
- if any validator rule consumes `input-term result` status, the pipeline must write `input-term result` before that validator step runs
- this spec does not allow hidden dependence on a later-produced artifact

Default safe design for this spec:
- keep `validate_word_list.py` structural/completeness-focused
- add or reuse separate post-QA status-based check only if needed

### 4.4 Compatibility boundary

Backward compatibility is required only at these surfaces:
- `Outputs/01_words.md` block schema
- `## UNRESOLVED PART` section marker
- existing deterministic issue codes unless intentionally changed
- runner behavior that continues when parseable NW1 blocks exist
- existing `written block QA row` fields remain additive if artifact shape changes

Backward compatibility is not required for:
- legacy `UNRESOLVED_JSON` comment protocol
- obsolete helper wrappers with no meaningful active ownership
- outdated tests that assert superseded output schema

### 4.5 Minimal implementation bias

This refactor should prefer:
- additive fields in existing dataclasses over new class hierarchies
- one shared helper over multiple adapters
- one step manifest or command table over two hand-maintained lists
- deletion of obsolete compatibility code over new bridging layers

Prompt-boundary rule:
- prompt files are in scope only for naming/contract alignment with refactored typed artifacts
- prompt edits must not silently change accepted linguistic policy unless a separate spec explicitly approves that rule change

## 5) Invariants

- `clean + unresolved_part + omitted == processed - skipped`
- every block written under `## UNRESOLVED PART` is parseable by `mdproc.validation_core.iter_blocks(...)`
- every valid block not accepted into clean output is represented as `unresolved_part`, not omitted
- every omitted entry has no valid serializable NW1 block shape
- deterministic issue codes remain stable unless spec explicitly changes them
- no per-block unresolved reason comments are added to canonical NW1 output
- CLI and LangGraph NW1 surfaces preserve same observable continuation semantics for parseable NW1 output
- generation-time acceptance and validator-time generic-content checks share one rule source
- validator exit behavior is explicit and stable:
  - structural invalidity -> non-zero
  - omitted entries present -> non-zero
  - unresolved_part present with no omitted entries -> zero
  - clean-only output -> zero

## 6) Acceptance Criteria

- QA artifact clearly separates `results` from `issue_rows`, or uses equivalently distinct top-level names with no grain ambiguity.
- `results[*]` include explicit resolution metadata required to explain unresolved and omitted outcomes.
- Validator no longer depends on `UNRESOLVED_JSON` or `UNRESOLVED` comments to reason about unresolved NW1 state.
- Stale validator test asserting JSON unresolved comments is removed or rewritten to current contract.
- `process_requirement1.py` no longer needs to stringify hard-fail QA issues merely to recover codes later.
- Generator-side and validator-side generic-content marker lists are centralized into one source.
- CLI runner and LangGraph use same NW1 step contract and same parseable-block continuation logic.
- Shared parser path is used for QA entry extraction wherever feasible.
- Docs under `Tools/README.md` and `Tools/scripts/README.md` no longer describe obsolete unresolved JSON behavior.
- Prompt files remain behaviorally equivalent unless an explicitly approved prompt-rule change is part of implementation.

## 7) Non-Goals

- No change to NW2–NW4 block schemas.
- No change to semantics of `## UNRESOLVED PART` itself.
- No new repair loop, retry model, or human-in-the-loop workflow.
- No semantic change to existing accepted deterministic `de_1` rules unless required to complete SSOT refactor.
- No broad rearchitecture of NotebookLM or NW3/NW4.
- No NW3 query-script parity work in this spec.
- No new persistence layer or database for QA state.

## 8) Risks and Mitigations

- Risk: changing QA row schema breaks consumers.
  - Mitigation: preserve current issue-row fields additively and keep `results` grain separate from `issue_rows`.

- Risk: validator behavior changes while docs/tests still assume legacy unresolved comments.
  - Mitigation: patch docs and stale tests in same bounded change.

- Risk: CLI/LangGraph parity work pulls in NW3-specific behavior too early.
  - Mitigation: limit orchestration refactor to NW1 step manifest and NW1 continuation only; defer NW3 parity to separate spec if still needed.

- Risk: typed acceptance refactor changes current hard-fail routing accidentally.
  - Mitigation: lock current behavior with focused regression tests before moving issue plumbing.

- Risk: deleting compatibility helpers removes coverage for hidden consumers.
  - Mitigation: verify callers with GitNexus context/impact and source grep before removal.

## 9) Validation Plan

- proof target: QA row schema ships unresolved metadata
  - method: focused unit/integration test on QA report payload
  - evidence: `results[*]` include `input_index`, `resolution_status`, `origin_reason_code`, and `final_blocker_code`, while `issue_rows[*]` remain block-scoped

- proof target: validator no longer depends on unresolved JSON comments
  - method: focused validator tests and source inspection
  - evidence: no active validator path requires `UNRESOLVED_JSON` or `UNRESOLVED` comments to detect unresolved state, and validator truth table matches spec

- proof target: stale unresolved-comment test surface is removed or updated
  - method: targeted pytest run
  - evidence: `py -m pytest Tools/tests/test_validate_word_list_script.py -q` passes under current contract

- proof target: generation-time acceptance uses typed issue/result data
  - method: focused unit test on `process_requirement1.py`
  - evidence: no string-roundtrip is needed to recover blocker codes

- proof target: generator and validator share one generic-content rule source
  - method: shared-fixture tests plus source inspection
  - evidence: one NW1-owned shared helper/constants module is imported by both call sites

- proof target: CLI and LangGraph NW1 paths are parity-aligned
  - method: focused orchestration parity test
  - evidence: same NW1 step set and same parseable-block continuation rule are asserted in both surfaces

- proof target: omitted entries are represented despite having no written block
  - method: focused integration test with one omitted candidate
  - evidence: `results[*]` contain omitted row for that `input_index`, while `issue_rows[*]` do not invent a fake block row

- proof target: validator exit policy is executable and stable
  - method: focused validator tests covering clean-only, unresolved_part-only, omitted-present, and structural-invalid cases
  - evidence: expected exit codes match invariant truth table

- proof target: valid unresolved tail remains parseable and count-invariant safe
  - method: focused integration test
  - evidence: `iter_blocks(...)` reads both main and unresolved sections and count invariant holds

- proof target: obsolete prompt/runtime leftovers are either removed or explicitly justified
  - method: source inspection and targeted tests
  - evidence: dead constants or wrappers are gone, or remaining ones have active callers and tests

## 10) Completion Criteria

- Detailed refactor spec approved.
- Follow-on implementation plan created for bounded NW1 refactor only.
- Plan explicitly sequences `R1` through `R7`, with `R1` first and `R5` gated behind narrower parity proof.
- Validation suite proves current-contract alignment across generator, validator, QA review, and orchestration.
- Docs and tests no longer describe or assert superseded unresolved-comment behavior.
- Artifact grain, ordering, identity key, and validator exit semantics are explicit enough that two implementers would produce same contracts.
