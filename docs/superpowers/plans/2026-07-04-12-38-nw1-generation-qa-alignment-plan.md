---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: nw1-generation-qa-alignment
parent_thread: current-thread
parent_spec: docs/superpowers/specs/2026-07-04-00-00-nw1-de1-sentence-and-target-realization-spec.md
targets:
  - Tools/scripts/process_requirement1.py
  - Tools/src/gnw_pipeline/nw1_qa.py
  - Prompt/nw1_enrich_instructions.md
  - Tools/tests/test_process_requirement1_failure_contract.py
  - Tools/tests/test_validation_core.py
related_features:
  - nw1-generation
  - nw1-qa
related_stages:
  - NW1
---

# Note (canonical template gap)

Repo paths required by `skill-writing-plans` are missing locally. This plan follows current repo frontmatter and section shape.

# Goal

Move existing NW1 `de_1` quality contract from report-only QA into generation-time acceptance so invalid LLM-repaired entries are rejected before `Outputs/01_words.md` is written.

# Scope

- In scope: generation-time reuse of SSOT `de_1` QA, prompt tightening for NW1 enrich, focused regression tests for exact bad terms, and minimal helper extraction if `process_requirement1.py` needs entry-aware QA input.
- In scope files are limited to `Tools/scripts/process_requirement1.py`, `Tools/src/gnw_pipeline/nw1_qa.py`, `Prompt/nw1_enrich_instructions.md`, `Tools/tests/test_process_requirement1_failure_contract.py`, and `Tools/tests/test_validation_core.py`.
- Out of scope: post-pass auto-repair loop, quarantine/filtering, parser or morphology engine, broad pipeline redesign, and changes to NW2–NW4.

# Diagnosis

- Current bad outputs are not fallback templates. They are accepted LLM repair results.
- Current acceptance gate in `process_requirement1.py` only checks generic markers, noun-shape rules, and meaning rules.
- Current gate does not run sentence-shape or target-realization checks already owned by `Tools/src/gnw_pipeline/nw1_qa.py`.
- Prompt contract in `Prompt/nw1_enrich_instructions.md` says `de_1` must be natural German, but does not require full sentence, target realization, or ban ellipsis and bare lemma output.
- Result: entries like `Ich möchte nicht, dass …`, `in der Kinderkrippe sein`, and `mitunter` can pass repair-time validation and reach final output.

# Resolution Contract

1. `process_requirement1.py` must reject repaired entries when SSOT `de_1` QA finds hard-fail issues.
2. Generation-time acceptance must use same deterministic `de_1` contract as report-time QA.
3. Prompt must explicitly require complete sentence, no ellipsis, no bare lemma or phrase, and direct target realization in `de_1`.
4. Retry behavior must stay bounded; this patch must not introduce unbounded repair loops.
5. Report-time QA stays in place as audit backstop even after generation-time enforcement is added.
6. Verb handling in this patch must reuse stored explicit forms; no guessed morphology engine.

# Key Deliverables

1. One generation-time QA bridge from `process_requirement1.py` into SSOT `qa_entry_issues(...)` or equivalent shared helper.
2. One tightened NW1 enrich prompt with explicit `de_1` acceptance rules.
3. One focused regression suite that reproduces exact bad examples and proves they are rejected.
4. One optional smoke-run recipe for rerunning NW1 on controlled input after patch lands.

# Task Breakdown

## Task 1 — Reuse SSOT QA at generation-time

**Files**
- `Tools/scripts/process_requirement1.py`
- `Tools/src/gnw_pipeline/nw1_qa.py`

**Work**
- Inspect current `validate_entry_quality(...)` path and keep generic marker checks already there.
- Reuse one shared parser or constructor from `nw1_qa.py` to build `QaEntry` for generation-time checks.
- Reuse `qa_entry_issues(...)` directly if current API already fits.
- If current QA module lacks one tiny helper needed by generator, add it in `nw1_qa.py` rather than duplicating parser or rule logic in `process_requirement1.py`.
- Treat hard-fail deterministic QA issues as repair rejection.
- Keep all soft-review deterministic QA issues non-blocking in this patch.
- Preserve current bounded retry loop and repeated-issue stop behavior.

**Verification**
- Exact bad repairs now return quality issues during repair-time acceptance.
- Valid sentence using stored target still passes same path.
- No duplicated sentence-shape or target-realization logic lives in `process_requirement1.py`.

## Task 2 — Tighten NW1 enrich prompt contract

**Files**
- `Prompt/nw1_enrich_instructions.md`

**Work**
- Add explicit `de_1` rules:
  - must be one complete German sentence
  - must end with `.`, `!`, or `?`
  - must not contain ellipsis `...` or `…`
  - must not be bare lemma, bare phrase, or dictionary-style fragment
  - must directly realize target term, not paraphrase only
- Keep wording tight and output-focused.
- Do not add vague linguistic theory or large examples block unless needed for failure prevention.

**Verification**
- Prompt text clearly forbids three observed failures: `Ich möchte nicht, dass …`, `in der Kinderkrippe sein`, `mitunter`.
- Prompt still preserves existing noun and verb field rules.

## Task 3 — Add focused regression tests for exact failures

**Files**
- `Tools/tests/test_process_requirement1_failure_contract.py`
- `Tools/tests/test_validation_core.py`

**Work**
- Add repair-path tests proving generation-time rejection for:
  - target `ich würde nicht wollen, dass …` with generated `de_1: Ich möchte nicht, dass …`
  - target `in der Kinderkrippe sein` with generated `de_1: in der Kinderkrippe sein`
  - target `mitunter` with generated `de_1: mitunter`
- Keep one SSOT QA test proving these failures map to expected issue codes and severities.
- Add one positive control proving valid realized sentence still passes repair-time gate.

**Verification**
- Repair-path tests fail before patch, pass after patch.
- SSOT QA tests and generator-path tests agree on reject and pass outcome.

## Task 4 — Optional smoke rerun

**Files**
- no new source target beyond existing scripts and reports

**Work**
- Keep repo-local tests as approval gate.
- If extra confidence is wanted, rerun NW1 on small controlled sample first.
- If local environment matches user machine, optionally rerun target live input used in user report.
- Inspect output and latest QA report for three known bad entries.
- Confirm bad entries are absent from final output or remain unresolved rather than silently accepted.

**Verification**
- Optional smoke only: `run_latest.log` shows repair rejection or unresolved status for known failures.
- Optional smoke only: `Outputs/01_words.md` no longer contains bad accepted examples for those targets.
- Optional smoke only: `Outputs/reports/nw1_qa_latest.json` still reports any unresolved issues as audit evidence.

# Validation Rules

- Hard-fail deterministic QA must block generation-time acceptance.
- Soft-review deterministic QA must not become blocking unless spec later says so.
- Same `de_1` contract must stay SSOT in `Tools/src/gnw_pipeline/nw1_qa.py`.
- `process_requirement1.py` must reuse shared `QaEntry` construction and must not own duplicate parser, sentence-shape, or target-realization policy.
- Prompt tightening alone is not sufficient; acceptance gate reuse is required.

# Risky Migrations

- Importing QA module into generation path can create coupling if helper API is too broad.
- Over-blocking soft-review issues could drop too many valid entries.
- Entry parsing inside generator can drift from report parser if not kept minimal and field-name exact.

# Best Lazy Implementation

- Reuse `qa_entry_issues(...)` from `nw1_qa.py`.
- Reuse one shared `QaEntry` parser or constructor from `nw1_qa.py`.
- Reject only `hard_fail` issues at generation-time.
- Tighten prompt, but trust validator over prompt.
- Add only exact regression tests for observed failures plus one positive control.

# Verification

- `py -m pytest Tools/tests/test_process_requirement1_failure_contract.py -q`
- `py -m pytest Tools/tests/test_validation_core.py -q`
- `py Tools/scripts/nw1_qa_review.py --root .`
- optional smoke: controlled NW1 rerun
- optional smoke on matching local environment: rerun `C:\Users\HOANG PHI LONG DANG\OneDrive\OBSIDIAN 24 09 01\24 09 01 obsidian-go-obsidian_v.0.3.1\German_New_Words\Inputs\Word List (DE).md`
