---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: langgraph-pydanticai-german-newwords-pipeline
parent_workstream: none
targets:
  - Tools/
  - Requirement/
  - Outputs/
---

# Spec: LangGraph + PydanticAI pipeline for German_NewWords (NW1–NW4)

## Note (canonical template gap)

Repo missing canonical template sources referenced by skill (`docs/operating_system/...`). This spec follows required section set from skill, but cannot inherit template wording verbatim.

## 1) Goal

Build single pipeline: input German words/phrases → output final structured vocabulary database (Pydantic models) + export Markdown compatible with current NW1–NW4 file surfaces.

Pipeline must:
- follow NW1 enrichment rules (templates, example quality, unresolved handling)
- follow NW2 normalization rules
- follow NW3 `see_also` generation + merge rules
- follow NW4 `see_also` normalization + validation rules
- enforce SSOT, symmetry, invariance: rules defined once, reused across graph paths

## 2) Key Deliverables

1. LangGraph graph (nodes + tool nodes) that produces:
   - Pydantic `FinalVocabDatabase` object (primary SSOT deliverable)
   - current Markdown outputs in `Outputs/` (compat surface)
2. SSOT rules layer:
   - Pydantic models (types + invariant validators)
   - deterministic normalizers + deterministic validators
   - LLM quality review gate emitting same violation schema (no parallel validator logic)
3. Minimal review outputs (low-noise, trendable):
   - `Outputs/reports/run_latest.json` (overwrite)
   - `Outputs/reports/runs.jsonl` (append-only, dedup by run_id)

## 3) Task/Wave Breakdown

### Wave A — SSOT foundations (no LangGraph yet)
- Define Pydantic models:
  - `VocabEntry`, `SeeAlsoRef`, `FinalVocabDatabase`
  - `Violation`, `RuleId`, `ReviewResult`
- Define deterministic normalizers (idempotent) and validators (pure) for NW1–NW4.
- Define conversions:
  - `ReviewResult -> list[Violation]` (same schema as deterministic checks)

### Wave B — LangGraph orchestration
- Define LangGraph `State` model.
- Implement thin nodes (orchestration only):
  - call SSOT helpers
  - route pass/fail/retry using shared `RetryPolicy`
- Implement tool node:
  - NotebookLM adapter returning structured JSON (validated with Pydantic)

### Wave C — Output surfaces + minimal review artifacts
- Keep existing Markdown filenames in `Outputs/` (overwrite each run).
- Add reports in `Outputs/reports/` with run_id dedup and quality trend metrics.

## 4) Design Decisions

### 4.1 SSOT boundary (models + rules)

SSOT = `models/ + rules/ + validators/ + normalizers/`.

LangGraph nodes must not embed:
- denylist strings
- regex parsing rules for `see_also`
- tag allowlist/mapping
- word hygiene rules (articles/gloss removal)

All such logic lives in SSOT helpers so every codepath reuses same checks.

### 4.2 Symmetry: one quality-gate harness

All “validate → (optional) normalize → validate → repair → validate” loops use same harness:
- vocab entry enrichment loop (NW1)
- `see_also` tool output parse/repair loop (NW3/NW4)
- final DB validation loop (NW4)

This prevents duplicated retry logic and duplicated error formatting.

### 4.3 Invariance: idempotent normalizers

Deterministic normalizers must be idempotent:
- running twice yields same result
- safe to apply at multiple checkpoints without drift

### 4.4 LLM quality review gate (post-deterministic)

Problem: denylist catches known bad patterns only; misses mixed-language, unnatural examples.

Decision:
- keep deterministic denylist as `RuleCheck`s (NW1 anti-placeholder, hard bans)
- add LLM reviewer after deterministic pass, before file/DB finalization
- reviewer emits `ReviewResult` and converts to `Violation[]` using same schema

Reviewer must cite evidence substring (exact snippet) for any `fail` issue to reduce hallucinated critiques.

### 4.5 Minimal output set (review + trend)

No new per-entry debug files by default.

Emit only:
- `Outputs/reports/run_latest.json` (overwrite)
- `Outputs/reports/runs.jsonl` (append-only)

Optional: add `Outputs/reports/checkpoints.jsonl` only if needed; default off.

### 4.6 Concrete LangGraph tool node recommendation (NotebookLM MCP)

Tool node contract must be stable, timeout-bounded, and batch-adaptive.

**Tool node inputs (state fields)**
- `words_subset: list[str]` (current batch)
- `notebook_id: str | None` (or `notebook_name`)
- `session_id: str | None` (reuse within run)
- `timeout_ms: int` (per-call browser timeout)

**Tool node outputs (state fields)**
- `seealso_items: list[{word: str, see_also: list[SeeAlsoRefDraft]}]` (structured)
- `missing_words: list[str]` (subset not returned / parse-failed)
- `tool_telemetry: {attempt:int, batch_size:int, elapsed_ms:int, timed_out:bool}` (for run report)

**Behavior**
- Call NotebookLM MCP `ask_question` with strict timeout (via `browser_options.timeout_ms`) and a prompt that forces JSON-only output.
- Validate tool output with Pydantic; on schema failure, treat as transient and retry once with a “re-emit valid JSON only” repair prompt.
- Never block indefinitely: enforce hard per-call timeout and hard per-stage wall-clock budget.

**Batch sizing strategy (AIMD)**
- Maintain `batch_size` in state.
- Start `B0=20` (configurable).
- On success: `B = min(B*2, B_max)` (default `B_max=60`).
- On timeout/hang/transient failure: `B = max(ceil(B/2), B_min)` (default `B_min=1`) and retry.
- If `B==B_min` and still failing: fall back to single-word calls for remaining items.

**Retry policy**
- Retry only for transient classes: timeout, rate-limit symptoms, browser navigation transient, schema parse failure.
- Backoff with jitter: 1s, 2s, 4s, 8s (cap 30s), max 3 attempts per batch before split.
- Requeue only `missing_words` after partial success; do not resend already-covered words.

**Session policy**
- Reuse `session_id` for all calls targeting same notebook within run.
- If N consecutive timeouts (default 3): trip circuit breaker, reset session, and continue with smaller batch; if still failing, fail stage with actionable error.

### 4.7 Recommended minimal UX (Windows .exe)

Goal: end user does not learn CLI; double-click `.exe` runs same pipeline contract.

**Distribution contract (minimal)**
- Ship:
  - `GermanNewWords.exe`
  - `GermanNewWords.runtime/` (bundled Python runtime + app dependencies; may include NotebookLM MCP runtime if feasible)

**Runtime behavior**
- UI mode: start as console-first `.exe` (lowest complexity), with option to evolve to tiny GUI later.
- Steps executed (same as pipeline):
  1. Check input file: `Inputs/Word List (DE).md` exists and non-empty.
  2. NotebookLM auth bootstrap:
     - If auth missing/expired, launch interactive auth (Chrome) and resume.
  3. Run pipeline through NW4.
- Logs:
  - Always write `Outputs/logs/run_latest.log` (overwrite each run).
  - Optionally keep `Outputs/logs/runs.jsonl` for history (append-only, dedup by run_id).
- Success UX:
  - Print/notify: path to `Outputs/06_words_final_fixed.md`.
  - Optionally auto-open `Outputs/06_words_final_fixed.md` on success.
- Failure UX:
  - Print/notify actionable next step (missing input, auth needed, MCP unreachable, validation failed).
  - Exit code reflects failure class.

**Invariants**
- `.exe` is a wrapper only: must not duplicate pipeline logic; it calls same SSOT modules and/or pipeline runner entrypoint.
- `.exe` must not introduce new duplicate Markdown outputs.

## 5) Invariants

### 5.1 Output compatibility invariants (current surfaces preserved)

Pipeline overwrites each run:
- `Outputs/01_words.md`
- `Outputs/02_words_fixed.md`
- `Outputs/03_word_list.md`
- `Outputs/04_see_also.md`
- `Outputs/05_see_also_fixed.md`
- `Outputs/06_words_final.md`
- `Outputs/06_words_final_fixed.md`

No timestamped duplicates in `Outputs/`.

### 5.2 Final deliverable invariants

Primary deliverable (SSOT):
- in-memory `FinalVocabDatabase` (Pydantic)

Secondary exports:
- Markdown files above (compat)
- optional JSON dump:
  - `Outputs/07_vocab_db.json` (if enabled)

### 5.3 NW1 invariants (enrichment)

- reorder: words first, phrases second; sort A–Z (ignore leading `der/die/das` for sort key only)
- dedupe within run, case-insensitive
- `word` hygiene: no parenthetical gloss; noun `word` not start with `der/die/das`
- examples: `de_1` German-only (allow proper nouns), speaking-oriented, no generic shells
- unresolved meaning: do not fabricate; mark unresolved and exclude from DB

### 5.4 NW3 invariants (`see_also` merge)

- `see_also` refs generated from `Outputs/03_word_list.md` coverage, not hardcoded list size
- merge only into matching `WORD` entries
- per-entry `see_also` dedupe keeps first-seen order
- Markdown placement rule preserved on export (above `Tags`, else above `EEND`)

### 5.5 NW4 invariants (`see_also` canonical + noun consistency)

- canonical `see_also` syntax on export:
  - noun refs include gender (`der/die/das`) with exactly one space before `[...|nid...]`
  - nid normalized (no `< >`, digits only)
  - no spaces inside brackets
- non-phrase blocks require non-empty `see_also` (per NW4)
- noun `noun_forms` present and consistent with `noun_genetiv` and `noun_plural`
- umlaut hygiene: avoid ASCII transliteration (`ae/oe/ue`) in German-facing fields and in `see_also` related words

## 6) Validation Plan

### Proof target: NW1 content quality gates enforceable
- Method: deterministic validation + LLM review (evidence-based issues)
- Evidence:
  - `Outputs/reports/run_latest.json` includes:
    - counts of deterministic fails
    - LLM QA fail rate + issue histogram
    - top N fail examples with evidence snippet
  - `Outputs/01_words.md` contains only valid entries + unresolved list (if any)

### Proof target: NW2 normalization applied
- Method: inspection + script run (where available)
- Evidence:
  - `Outputs/02_words_fixed.md` exists and differs only by normalization transforms
  - `Outputs/03_word_list.md` exists; count matches blocks in `02_words_fixed.md` (minus unresolved)

### Proof target: NW3 coverage and merge correctness
- Method: validator comparing word_list coverage vs see_also blocks + merge audit
- Evidence:
  - `Outputs/reports/run_latest.json` shows:
    - `word_list` count
    - `04_see_also.md` coverage
    - merged count into `06_words_final.md`
  - `Outputs/06_words_final.md` contains merged `see_also` only; other fields unchanged from `02_words_fixed.md`

### Proof target: NW4 strict compliance
- Method: run authoritative validator (existing tooling) + SSOT validators
- Evidence:
  - `Outputs/06_words_final_fixed.md` produced
  - `Tools/scripts/validate_requirement4.py` passes (or pipeline equivalent emits `nw4_pass=true`)

### Proof target: low-noise quality trend
- Method: compare `runs.jsonl` over time
- Evidence:
  - `Outputs/reports/runs.jsonl` contains 1 line per distinct run_id with key rates (LLM QA fail, missing see_also, nw4 pass/fail)

## 7) Acceptance Criteria

1. Running pipeline produces all 7 existing Markdown outputs with same names (overwrite, no duplicates).
2. Deterministic validators catch NW1 anti-placeholder patterns and structural/template requirements.
3. LLM QA gate flags mixed-language `de_1` (ex English tokens) and routes to repair, with evidence snippet recorded.
4. `see_also` merge respects NW3 behavior (dedupe per entry, first-seen order preserved).
5. NW4 final output meets canonical `see_also` formatting and noun consistency checks; validator passes.
6. Only 2 report files emitted by default:
   - `Outputs/reports/run_latest.json`
   - `Outputs/reports/runs.jsonl`
7. `runs.jsonl` shows monotonic trendability (stable metric keys; one row per run_id).

## 8) Non-Goals

- No UI, no Obsidian automation, no Anki import automation in this spec.
- No refactor of existing `mdproc` toolchain unless required for correctness.
- No bulk storage of per-entry QA traces by default (only top N examples in `run_latest.json`).

## 9) Risks and Mitigations

- Risk: NotebookLM returns unstructured/variable output.
  - Mitigation: tool contract requires structured JSON; validate with Pydantic; targeted requery loop for gaps/non-canonical.
- Risk: LLM reviewer inconsistent/hallucinates.
  - Mitigation: require evidence snippet for `fail`; convert to same `Violation` schema; cap retries; allow `warn` non-blocking.
- Risk: duplicated validators creep back in nodes.
  - Mitigation: enforce “thin node” rule in code review; centralize rules in SSOT modules; forbid inline denylist in nodes.

## 10) Completion Criteria

- Spec accepted by user.
- Implementation (separate phase) yields:
  - pipeline run produces required outputs
  - `Outputs/reports/run_latest.json` and `runs.jsonl` generated
  - NW4 validation passes on `Outputs/06_words_final_fixed.md`
