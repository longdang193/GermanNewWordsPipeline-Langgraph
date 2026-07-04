---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: nw1-partial-output-failure-guard
parent_thread: current-thread
parent_spec: none
targets:
  - Tools/scripts/process_requirement1.py
  - Tools/scripts/validate_word_list.py
  - Tools/scripts/run_full_pipeline.py
  - Tools/tests/test_validate_word_list_script.py
  - Tools/tests/test_process_requirement1_failure_contract.py
  - Tools/README.md
related_features:
  - nw1-generation
  - nw1-validation
related_stages:
  - NW1
---

# Goal

Stop NW1 from passing unless all required entries resolve successfully, surface root-cause evidence early, and keep downstream stages from consuming partial output as success.

# Key Deliverables

- Exact NW1 success invariant shared across generator, validator, and pipeline.
- Root-cause summary in NW1 generation output with sampled unresolved reason codes.
- Tests covering strict failure behavior and reason-code reporting.
- Docs aligned with real validator semantics.

# Task Breakdown

## Task 1 — Tighten NW1 success contract

**Files**
- `Tools/scripts/validate_word_list.py`
- `Tools/tests/test_validate_word_list_script.py`
- `Tools/README.md`

**Work**
- Define one exact invariant in `Tools/scripts/validate_word_list.py`: default NW1 passes only when generated block count equals expected required count and unresolved count is zero.
- Remove unresolved-based success from validator; no partial-mode escape hatch in validator or pipeline for this patch.
- Make failure message say exact counts: processed, generated blocks, unresolved count, expected coverage.
- Add/adjust tests for:
  - unresolved entries cause failure by default
  - JSON unresolved parsing still handles commas safely
- Update `Tools/README.md` so exit-code docs match code.

**Verification**
- `py -m pytest Tools/tests/test_validate_word_list_script.py`
- `C:\Users\HOANG PHI LONG DANG\AppData\Local\Programs\Python\Python313\python.exe Tools/scripts/validate_word_list.py` against current bad output should exit non-zero.

## Task 2 — Surface root cause at generation step

**Files**
- `Tools/scripts/process_requirement1.py`
- `Tools/tests/test_process_requirement1_failure_contract.py`

**Work**
- Change resolver contract to return explicit reason codes for unresolved terms instead of relying on exception-text parsing.
- Keep existing unresolved collection, but treat any unresolved term as strict failure in normal execution.
- Add compact failure summary by reason code with sampled terms:
  - `missing_meaning`
  - `missing_de_example`
  - `missing_en_example`
  - `llm_auth_failed`
- Define failure artifact contract: in strict mode, do not write canonical `Outputs/01_words.md` on failure. If debug artifact is needed, write separate `Outputs/01_words.partial.md`.
- Add hermetic tests for resolver/generator failure contract and reason-code bucketing.

**Verification**
- `py -m pytest Tools/tests/test_process_requirement1_failure_contract.py`
- Confirm strict-failure path does not leave canonical `Outputs/01_words.md` behind.

## Task 3 — Stop downstream false-success pipeline flow

**Files**
- `Tools/scripts/run_full_pipeline.py`

**Work**
- Check NW1 generation exit code explicitly and stop before validator when generation fails.
- Preserve validator as second guard, but ensure NW1 generation failure or strict NW1 validation failure blocks NW2/NW3/NW4.
- If optional NW1 QA remains gated by env, do not rely on it for correctness; correctness must come from generation/validation contract.

**Verification**
- Add or update one narrow test if pipeline script has test surface; otherwise keep manual smoke check only.
- Manual smoke check: run `C:\Users\HOANG PHI LONG DANG\AppData\Local\Programs\Python\Python313\python.exe Tools/scripts/run_full_pipeline.py` and confirm pipeline stops in NW1 before downstream stages.

## Task 4 — Fresh regression checks

**Files**
- `Outputs/01_words.md` as runtime artifact only
- `Outputs/01_words.partial.md` only if debug artifact is retained

**Work**
- Keep approval checks hermetic where possible: temp-file validator tests and generator failure-contract tests are approval gate.
- Keep one manual smoke run separate from approval gate: rerun NW1 with current env to confirm failure is loud and accurate.
- Future content-complete run with valid env or expanded overrides is follow-up validation, not required to approve this patch.

**Verification**
- Hermetic tests pass without depending on local LLM credentials.
- Manual smoke run shows strict failure with exact unresolved counts and no canonical partial artifact.

# Verification

- `py -m pytest Tools/tests/test_validate_word_list_script.py`
- `py -m pytest Tools/tests/test_process_requirement1_failure_contract.py`
- Manual smoke: `C:\Users\HOANG PHI LONG DANG\AppData\Local\Programs\Python\Python313\python.exe Tools/scripts/process_requirement1.py`
- Manual smoke: `C:\Users\HOANG PHI LONG DANG\AppData\Local\Programs\Python\Python313\python.exe Tools/scripts/validate_word_list.py`
- Manual smoke: `C:\Users\HOANG PHI LONG DANG\AppData\Local\Programs\Python\Python313\python.exe Tools/scripts/run_full_pipeline.py`

# Notes

- This patch plan fixes false success first. It does not promise to author 101 lexical overrides.
- Content completion is separate follow-up: either provide working LLM env or add curated overrides/examples for missing terms.
- No validator/pipeline partial mode in this patch. One strict path keeps SSOT and keeps failure semantics symmetric.
