---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: centralize-llm-runtime-config-ssot
parent_thread: current-thread
parent_spec: none
targets:
  - Tools/src/gnw_pipeline/runtime_config.py
  - Tools/src/gnw_pipeline/llm_runtime.py
  - Tools/src/gnw_pipeline/nw1_llm_enrich.py
  - Tools/scripts/process_requirement1.py
  - Tools/scripts/nw1_qa_review.py
  - configs/runtime.toml
  - .env.example
  - README.md
  - Tools/tests/test_llm_runtime.py
  - Tools/tests/test_process_requirement1_failure_contract.py
related_features:
  - nw1-generation
  - llm-runtime
related_stages:
  - NW1
---

# Goal

Move NW1/LLM settings to one central config layer with clear ownership, so model selection, base URL, API key env names, and enable flags do not drift across scripts, loaders, and docs.

# Scope

- In scope: NW1 LLM runtime path only.
- In scope files are limited to NW1/LLM runtime loader, NW1 enrich caller paths, docs, and tests named below.
- Out of scope for this patch: unrelated env/proxy handling, NotebookLM auth config, and repo-wide generic env abstraction.

# Diagnosis

- LLM runtime behavior is split today:
  - `configs/runtime.toml` holds only partial LLM config.
  - `.env` holds endpoint/model credentials.
  - code reads raw env keys directly in multiple places.
- Ownership is blurry:
  - runtime behavior and env key names are partly hardcoded in code.
  - docs describe values without one authoritative schema.
- Result: one developer can change `.env`, another `runtime.toml`, another defaults in code, and all three think they changed “the config”.

# Proposed Config Structure

- Keep **environment secrets and machine-local endpoint values** in `.env`.
- Keep **runtime config schema, defaults, and feature flags** in `configs/runtime.toml`.
- Make `Tools/src/gnw_pipeline/runtime_config.py` the sole loader/validator for non-secret runtime config.
- Make `Tools/src/gnw_pipeline/llm_runtime.py` the sole boundary allowed to read `OPENAI_*` env values.

# Resolution Contract

Resolution order must be exact and shared:

1. load typed runtime policy from `configs/runtime.toml`
2. load `.env` into process environment if keys are not already present
3. resolve `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` from environment only
4. if `OPENAI_MODEL` is missing or empty, use `llm.default_model`
5. if NW1 LLM enrich is disabled, skip LLM value validation entirely
6. if NW1 LLM enrich is enabled:
   - `OPENAI_API_KEY` is required
   - `OPENAI_BASE_URL` is optional only when runtime policy says direct OpenAI default is allowed
   - otherwise missing required values fail loudly with actionable message

# Key Deliverables

- One typed SSOT for LLM runtime config in `runtime_config.py`.
- One `configs/runtime.toml` section defining stable keys for NW1/LLM behavior.
- Raw env access removed from NW1 code paths except inside `llm_runtime.py`.
- Tests covering config resolution precedence and failure modes.
- Docs updated to reflect exact config ownership.

# Task Breakdown

## Task 1 — Define central config contract

**Files**
- `Tools/src/gnw_pipeline/runtime_config.py`
- `configs/runtime.toml`
- `.env.example`

**Work**
- Add typed config for LLM env/runtime settings, for example:
  - `llm.default_model`
  - `llm.allow_default_openai_base_url`
  - `nw1.enable_llm_enrich`
- Keep secrets out of `runtime.toml`; only store defaults, flags, and policy.
- Validate required keys, sane defaults, and allowed combinations in one place.
- Preserve current repo split:
  - `.env` = machine-local values
  - `runtime.toml` = runtime contract and policy

**Verification**
- Loader tests prove default config shape and validation.
- One small config fixture proves bad config fails loudly.

## Task 2 — Refactor LLM runtime to consume central config

**Files**
- `Tools/src/gnw_pipeline/llm_runtime.py`
- `Tools/src/gnw_pipeline/nw1_llm_enrich.py`
- `Tools/scripts/process_requirement1.py`
- `Tools/scripts/nw1_qa_review.py`

**Work**
- Remove direct hardcoded env-key knowledge from callers.
- Centralize env resolution in LLM runtime boundary:
  - load runtime config
  - load `.env`
  - resolve actual API key/base URL/model from stable `OPENAI_*` env names
- Replace direct reads of:
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL`
  - `GNW_ENABLE_NW1_LLM_ENRICH`
  where appropriate with typed config access.
- Keep compatibility shim only for legacy enable-flag behavior if needed, and only in central loader/runtime boundary.

**Verification**
- Existing LLM runtime tests updated.
- New tests prove config-driven env resolution works with temp env values.

## Task 3 — Make NW1 behavior symmetric and testable

**Files**
- `Tools/tests/test_llm_runtime.py`
- `Tools/tests/test_process_requirement1_failure_contract.py`

**Work**
- Add hermetic tests for:
  - enable/disable NW1 LLM enrich via central config
  - model resolution from env value with fallback to `llm.default_model`
  - base URL resolution from env value with policy-controlled optionality
  - missing required env values produce actionable failure
- Ensure tests do not require live network.

**Verification**
- `py -m pytest Tools/tests/test_llm_runtime.py Tools/tests/test_process_requirement1_failure_contract.py`

## Task 4 — Update docs and migration notes

**Files**
- `README.md`
- `.env.example`
- `configs/runtime.toml`

**Work**
- Document exact ownership boundary:
  - `runtime.toml` = config schema/defaults/flags
  - `.env` = actual secret and endpoint values
- Document exact required keys for Option A.
- Add one migration note for existing `OPENAI_*` users if compatibility shim retained.

**Verification**
- Docs mention one authoritative config path for runtime rules.
- `.env.example` matches runtime loader expectations.

# Validation Rules

- `runtime_config.py` must be able to build full typed config without callers knowing env-key names.
- No NW1/LLM call site outside `llm_runtime.py` should hardcode `OPENAI_*` names.
- `configs/runtime.toml` keys must validate for presence and type.
- `.env.example` must list only machine-local value variables, not duplicate runtime policy.
- Verification must include executable grep proving raw `OPENAI_*` reads remain only in allowed boundary.

# Risky Migrations

- Breaking current `.env` users if compatibility is removed too early.
- Moving too much into `runtime.toml`; secrets must stay out.
- Duplicating config parsing in both `runtime_config.py` and `llm_runtime.py`; loader must stay single-source.
- Making env-var names configurable would create new drift surface; this patch must not do that.

# Best Lazy Implementation

- Do not invent multiple new config files.
- Keep one existing `configs/runtime.toml` as runtime SSOT.
- Keep `.env` for machine-local values.
- Add only typed `llm` and `nw1` fields needed for this bugfix.
- Keep stable `OPENAI_*` names as external interface contract; do not make env-var names configurable.
- Keep one compatibility layer only for legacy enable-flag behavior if needed.

# Verification

- `py -m pytest Tools/tests/test_llm_runtime.py Tools/tests/test_process_requirement1_failure_contract.py`
- `py -m pytest Tools/tests/test_validate_word_list_script.py Tools/tests/test_processor.py Tools/tests/test_nw1_parallel.py`
- `rg -n "OPENAI_API_KEY|OPENAI_BASE_URL|OPENAI_MODEL|GNW_ENABLE_NW1_LLM_ENRICH" Tools/src Tools/scripts`
- Manual smoke after config patch: `C:\Users\HOANG PHI LONG DANG\AppData\Local\Programs\Python\Python313\python.exe Tools/scripts/process_requirement1.py`

# Notes

- This patch plan centralizes config ownership first; it does not promise the local OpenAI-compatible endpoint is healthy.
- If `127.0.0.1:20128` still returns `404`, content generation will still fail, but config drift will be gone and diagnosis will be cleaner.
