---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: nw1-de1-sentence-and-target-realization
parent_thread: current-thread
parent_spec: docs/superpowers/specs/2026-07-04-00-00-nw1-de1-sentence-and-target-realization-spec.md
targets:
  - Tools/src/gnw_pipeline/nw1_qa.py
  - Tools/scripts/nw1_qa_review.py
  - Tools/scripts/run_full_pipeline.py
  - Tools/src/gnw_pipeline/langgraph_app.py
  - Tools/tests/test_validation_core.py
related_features:
  - nw1-generation
  - nw1-qa
related_stages:
  - NW1
---

# Goal

Implement deterministic NW1 `de_1` QA so sentence fragments and lexeme-miss examples are reported through one SSOT schema, run automatically in both pipeline entrypoints, and do not mutate downstream artifacts.

# Scope

- In scope: deterministic `de_1` sentence-shape checks, deterministic target-realization checks, one unified QA report schema, QA script/report refactor, always-run deterministic QA wiring in both NW1 pipeline entrypoints, and focused tests.
- In scope files are limited to `nw1_qa.py`, `nw1_qa_review.py`, `run_full_pipeline.py`, `langgraph_app.py`, and focused NW1 QA tests in `test_validation_core.py`.
- Out of scope for this patch: post-pass auto-repair, quarantine/filtering, repo-wide QA framework, full German parsing, unstored verb conjugation generation, and changes to `process_requirement1.py`.

# Diagnosis

- Current deterministic NW1 QA is too weak and too narrow:
  - `qa_de1_issues(...)` only checks mixed-language English token leakage
  - it does not know `word`, `word_inf`, `tags`, or stored verb forms needed for lexeme-realization checks
- Current QA report contract is split and ad hoc:
  - deterministic rows go to top-level `issues`
  - optional LLM rows go to separate top-level `llm_issues`
- Current pipeline behavior is inconsistent:
  - CLI pipeline only runs NW1 QA when `GNW_ENABLE_NW1_QA=1`
  - LangGraph path also skips NW1 QA unless env gate is enabled
- Result:
  - fragment-like `de_1` can pass silently
  - paraphrase-only examples can pass silently
  - two entrypoints do not share same default QA behavior
  - downstream consumers do not have one stable machine-readable QA schema

# Resolution Contract

Resolution rules must be exact and shared:

1. deterministic NW1 QA must always run after structural NW1 validation in both `run_full_pipeline.py` and `langgraph_app.py`
2. deterministic NW1 QA remains report-only and must not rewrite `Outputs/01_words.md`
3. one authoritative issue/report schema must live in `Tools/src/gnw_pipeline/nw1_qa.py`
4. deterministic and optional LLM review rows must normalize into same top-level `rows` payload
5. `de_1` validation must answer two separate questions:
   - does sentence look like sentence?
   - does sentence realize target lexeme?
6. verb realization in v1 must rely on explicit stored forms only; no unstored conjugation guessing
7. same QA logic and same report shape must hold across both pipeline entrypoints

# Key Deliverables

- One SSOT QA layer in `Tools/src/gnw_pipeline/nw1_qa.py` containing:
  - deterministic issue schema
  - report-row schema helpers
  - sentence-shape checks
  - target-realization checks
  - optional LLM-row normalization helper
- One refactored `Tools/scripts/nw1_qa_review.py` that builds entry context, emits unified `rows`, and keeps optional LLM review non-mutating.
- One always-run deterministic NW1 QA step in `Tools/scripts/run_full_pipeline.py`.
- One always-run deterministic NW1 QA node behavior in `Tools/src/gnw_pipeline/langgraph_app.py`.
- Focused tests proving fragment detection, phrase realization, stored-form verb realization, soft-review behavior, unified report shape, and non-mutation behavior.

# Task Breakdown

## Task 1 — Extend `nw1_qa.py` into SSOT deterministic QA layer

**Files**
- `Tools/src/gnw_pipeline/nw1_qa.py`
- `Tools/tests/test_validation_core.py`

**Work**
- Keep current mixed-language detector, but move from single-purpose helper to shared deterministic QA layer.
- Add one authoritative issue model/shape for deterministic QA output.
- Add helper to derive one `match_mode` per entry from `word`, `word_inf`, `tags`, and stored verb fields.
- Add normalization helpers for:
  - lowercase compare
  - whitespace collapse
  - punctuation-trimmed tokens
  - article dropping for coverage compare
  - light adjective-ending folding for phrase realization
- Add sentence-shape checks:
  - terminal punctuation
  - forbidden terminal punctuation
  - minimum token count
  - lowercase initial alpha as `soft_review`
  - no-predicate cue as `soft_review`
- Add target-realization checks:
  - phrase/noun/adjective/adverb realization
  - explicit stored-form verb realization
  - same-clause split-form recognition only for already stored split forms
  - `soft_review` when sentence may use plausible but unstored conjugation
- Keep API small. Prefer one entry-level function, for example `qa_entry_issues(...)`, over growing multiple parallel functions.

**Verification**
- Add focused tests for:
  - mixed-language detection still works
  - `voller Leidenschaft und mit ganzem Einsatz` fails sentence-shape
  - `Voller Leidenschaft und mit ganzem Einsatz.` produces `soft_review`
  - `Er arbeitet voller Leidenschaft und mit ganzem Einsatz.` passes
  - `eine warme Umgebung` phrase examples pass/fail as specified
  - stored split-form verb example passes
  - unstored but plausible verb case becomes `soft_review`

## Task 2 — Refactor `nw1_qa_review.py` to use unified entry context and unified report payload

**Files**
- `Tools/scripts/nw1_qa_review.py`
- `Tools/tests/test_validation_core.py`

**Work**
- Stop calling deterministic QA with only `de_1` text.
- Extract full per-block context needed by deterministic QA:
  - `word`
  - `meaning`
  - `de_1`
  - `en_1`
  - `word_inf`
  - `Tags`
  - `verb_present`
  - `verb_past`
  - `verb_perfect`
- Replace split top-level arrays (`issues`, `llm_issues`) with one unified `rows` payload.
- Keep optional LLM review behind existing opt-in flag, but normalize any LLM issue into same row shape and tag `source = llm`.
- Preserve `--fail-on-issues`, but make it operate on unified rows and deterministic issue severity rather than ad hoc object counting.
- Keep report output path stable unless spec explicitly changes it.

**Verification**
- Add focused test or fixture proving report payload contains:
  - `input`
  - `rows`
  - `row_count`
  - `issue_count`
  - `env`
- Add focused test proving one row may contain deterministic issues and optional LLM-shaped issues under same `issues` contract.

## Task 3 — Make deterministic NW1 QA always run in CLI pipeline

**Files**
- `Tools/scripts/run_full_pipeline.py`

**Work**
- Remove env gating for deterministic NW1 QA step.
- Keep optional LLM review env-gated.
- Ensure deterministic QA still exits non-blocking by default and writes report artifact.
- Keep NW1 structural validation order unchanged: generation -> structural validation -> deterministic QA -> NW2.

**Verification**
- Command inspection or focused smoke check proves deterministic QA command is invoked without requiring `GNW_ENABLE_NW1_QA=1`.
- Existing structural-stop behavior remains unchanged when NW1 validation fails.

## Task 4 — Make deterministic NW1 QA always run in LangGraph pipeline

**Files**
- `Tools/src/gnw_pipeline/langgraph_app.py`

**Work**
- Remove skip behavior for deterministic `nw1_qa_review` node.
- Keep node in same order after NW1 validation.
- If env/config still controls optional LLM review, pass that only to script arguments or script-internal behavior, not to whether deterministic QA node exists.
- Preserve existing NW2–NW4 ordering.

**Verification**
- Focused code-path check proves `nw1_qa_review` node no longer resolves to `skipped` by default.
- Command step list still preserves NW1 -> QA -> NW2 order.

## Task 5 — Add report-only non-mutation proof

**Files**
- `Tools/tests/test_validation_core.py`

**Work**
- Add one focused integration-style test or helper proving NW1 QA does not rewrite `Outputs/01_words.md`.
- Keep proof minimal:
  - write small temporary NW1 sample
  - hash or byte-compare before/after QA review run
- Do not add new test framework.

**Verification**
- Focused test proves identical file content before and after QA review step.

# Validation Rules

- deterministic NW1 QA must be source-of-truth for sentence-shape and lexeme-realization checks
- same issue semantics must not be duplicated in `nw1_qa_review.py`
- same report payload shape must be emitted regardless of whether optional LLM review is enabled
- QA must not mutate `Outputs/01_words.md`
- verb realization must never depend on guessed unstored morphology in this patch
- deterministic QA must run by default in both CLI and LangGraph paths

# Risky Migrations

- Changing QA function signature from `qa_de1_issues(de_1)` to entry-aware context can break existing callers if not updated together.
- Unifying report payload can break any downstream consumer expecting `issues` / `llm_issues` top-level arrays.
- Removing env gating for deterministic QA can expose noisy false positives immediately.
- Same-clause split-form logic can still overmatch if punctuation/clause boundaries are handled loosely.

# Best Lazy Implementation

- Keep one module, `nw1_qa.py`, as SSOT for deterministic QA and row normalization helpers.
- Reuse existing `test_validation_core.py`; do not create a new QA-specific test suite unless current file becomes unmanageable.
- Replace split top-level report arrays with one `rows` payload in one pass.
- Keep deterministic QA report-only.
- Do not touch `process_requirement1.py` in this patch.
- Do not add parser, lemmatizer, or generic morphology engine.

# Verification

- `py -m pytest Tools/tests/test_validation_core.py -q`
- `py Tools/scripts/nw1_qa_review.py --root .`
- `py Tools/scripts/run_full_pipeline.py` with a small controlled NW1 sample only if safe local smoke run is needed
- Focused inspection of `Tools/src/gnw_pipeline/langgraph_app.py` node order if LangGraph test harness is not available

# Notes

- Repo-local canonical planning schema files referenced by skill are missing here; this plan follows existing repo plan shape and current validated frontmatter pattern.
- This patch intentionally chooses report-only behavior first. If later you want auto-repair or filtered corpus outputs, write follow-on spec and plan instead of growing this one in place.
