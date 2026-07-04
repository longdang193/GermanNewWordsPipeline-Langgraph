---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: nw1-validator-retry-repair
parent_thread: current-thread
parent_spec: none
targets:
  - configs/runtime.toml
  - Tools/src/gnw_pipeline/runtime_config.py
  - Tools/scripts/validate_word_list.py
  - Tools/scripts/process_requirement1.py
  - Tools/tests/test_validate_word_list_script.py
  - Tools/tests/test_process_requirement1_failure_contract.py
related_features:
  - nw1-generation
  - llm-runtime
related_stages:
  - NW1
---

# Goal

Fix NW1 contract drift so article-led noun entries from source are valid, add configurable bounded LLM repair retry, and print repair/retry trace lines during live runs.

# Scope

- In scope: NW1 noun validation contract, NW1 repair retry behavior, central retry config, and focused tests.
- In scope files are limited to runtime config, NW1 validator, NW1 processor, and focused NW1 tests named below.
- Out of scope for this patch: broader logging framework, repo-wide retry utility, and non-NW1 menu UX changes.

# Diagnosis

- Current NW1 contract is inconsistent:
  - source-word preservation now keeps entries like `word: das soziale Verhalten`
  - noun validator still rejects article-led noun phrases as “phrase-like”
- Current NW1 repair path is too weak:
  - `try_llm_enrich_override(...)` attempts LLM repair only once
  - failure reasons are mostly silent except final unresolved summary
- Result:
  - valid LLM-enriched noun entries can be discarded by outdated validator rules
  - transient or first-pass repair failures have no bounded retry
  - live debugging lacks clear attempt/retry output

# Resolution Contract

Resolution rules must be exact and shared:

1. `word:` may preserve source text for noun entries when source intentionally includes article-led noun expression
2. validator must allow article-led noun expressions when `word` and `word_inf` agree on the same phrase-level noun identity
3. NW1 LLM repair retry count must come only from central runtime config
4. retry must never loop forever; bounded by config with minimum `1`
5. auth failures must not retry
6. repair trace prints must show attempt, retry reason, success, and final failure when enabled

# Key Deliverables

- One central NW1 retry policy in `configs/runtime.toml` and `runtime_config.py`.
- One validator rule set aligned with current source-word preservation contract.
- One bounded retry loop in `process_requirement1.py` for NW1 LLM repair.
- One live-run print trace path for repair/retry behavior.
- Focused tests proving validator allowance, retry count, auth no-retry, and trace output.

# Task Breakdown

## Task 1 — Add central NW1 repair retry config

**Files**
- `configs/runtime.toml`
- `Tools/src/gnw_pipeline/runtime_config.py`

**Work**
- Add NW1 retry config fields:
  - `nw1.llm_repair_max_attempts`
  - `nw1.llm_repair_print_trace`
- Parse them into typed runtime config.
- Enforce minimum attempt count of `1`.
- Keep retry policy in repo config, not `.env`.

**Verification**
- Focused config tests prove typed values load correctly.
- One fixture proves zero/negative attempts clamp to `1`.

## Task 2 — Fix validator contract drift for article-led noun expressions

**Files**
- `Tools/scripts/validate_word_list.py`
- `Tools/tests/test_validate_word_list_script.py`

**Work**
- Relax noun-shape rejection for article-led noun expressions like `das soziale Verhalten`.
- Allow when:
  - `word` starts with valid article
  - `word_inf` matches same article-led noun phrase identity
- Preserve existing rejection for clearly phrase-like junk and bad guessed masculine lemmas.

**Verification**
- Add focused test that `das soziale Verhalten` passes noun-shape validation.
- Existing `Fahrstreifen` regression still passes.

## Task 3 — Add configurable bounded LLM repair retry

**Files**
- `Tools/scripts/process_requirement1.py`
- `Tools/tests/test_process_requirement1_failure_contract.py`

**Work**
- Change `try_llm_enrich_override(...)` from one-shot to bounded retry loop.
- Read max attempts from central NW1 config.
- Retry only on:
  - non-auth LLM exception
  - preview build failure
  - quality validation failure
- Do not retry auth failure.
- Return first valid override.

**Verification**
- Test retries stop after first success.
- Test auth failure does not retry.
- Test configured max attempts is honored.

## Task 4 — Add repair/retry trace prints

**Files**
- `Tools/scripts/process_requirement1.py`
- `Tools/tests/test_process_requirement1_failure_contract.py`

**Work**
- Print when repair starts.
- Print each retry with attempt count and reason.
- Print success.
- Print final failure after max attempts.
- Guard trace output with `nw1.llm_repair_print_trace`.

**Verification**
- Focused test captures stdout and proves trace lines appear when enabled.
- Focused test proves trace stays quiet when disabled.

# Validation Rules

- `word:` identity must remain stable across source extraction, repair, and validation for article-led noun expressions.
- Retry count must be defined in one place only: `Nw1RuntimeConfig` loaded from `configs/runtime.toml`.
- No auth retry allowed.
- Retry path must fail loudly after max attempts; no silent downgrade of quality gates.
- Verification must include executable proof for validator, retry count, no-auth-retry, and trace output.

# Risky Migrations

- Relaxing validator too broadly could allow real phrase junk through.
- Retry loop could hide deterministic content bugs if not bounded and transparent.
- Trace prints could become noisy if enabled unconditionally.
- Duplicating retry config in both code constants and TOML would recreate drift.

# Best Lazy Implementation

- Add only two NW1 config fields.
- Keep retry local to NW1 repair path; do not build generic retry framework.
- Use plain `print(...)` trace lines, not logging infra.
- Narrow validator change to article-led noun expressions that match `word_inf`.
- Keep strict unresolved stop after retries are exhausted.

# Verification

- `py -m pytest Tools/tests/test_validate_word_list_script.py -q`
- `py -m pytest Tools/tests/test_process_requirement1_failure_contract.py -q`
- Reproduce exact failing term with Python snippet for `das soziale Verhalten`
- `C:\Users\HOANG PHI LONG DANG\AppData\Local\Programs\Python\Python313\python.exe Tools\scripts\process_requirement1.py`

# Notes

- This patch fixes contract mismatch first; it does not promise every noun phrase should become valid.
- Retry is resilience, not semantic repair guarantee.
- If `das soziale Verhalten` still fails after validator alignment and bounded retry, add explicit lexical override rather than expanding heuristics further.
