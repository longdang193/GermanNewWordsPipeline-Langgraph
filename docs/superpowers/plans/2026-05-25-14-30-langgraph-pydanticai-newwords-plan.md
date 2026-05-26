---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: langgraph-pydanticai-german-newwords-pipeline-implementation
parent_spec: docs/superpowers/specs/2026-05-25-14-00-langgraph-pydanticai-newwords-spec.md
targets:
  - Tools/
  - Requirement/
  - Outputs/
  - docs/superpowers/specs/2026-05-25-14-00-langgraph-pydanticai-newwords-spec.md
---

# Implementation Plan: LangGraph + PydanticAI pipeline (NW1–NW4)

## Note (canonical template gap)

Repo missing canonical plan template + planning schema (`docs/operating_system/...`, `repo_config/planning_artifact_schema.yaml`). Plan follows required section shape from skill, but cannot conform to missing files verbatim.

## 1) Goal

Implement pipeline described in parent spec:
- SSOT Pydantic models + SSOT rules/validators/normalizers
- LangGraph orchestration with thin nodes
- NotebookLM MCP tool node with strict timeout + adaptive batching + retries
- Minimal review artifacts for quality trend (low noise, no duplicate md outputs)

## 2) Key Deliverables

1. New code module(s) under `Tools/` implementing:
   - `models/` (Pydantic)
   - `rules/`, `validators/`, `normalizers/` (SSOT)
   - `llm_review/` (ReviewResult -> Violation[] conversion)
   - `notebooklm_adapter/` (MCP client wrapper + batch planner)
   - `langgraph_app/` (graph builder + CLI entrypoint)
2. Pipeline run produces (overwrite each run):
   - `Outputs/01_words.md` → `Outputs/06_words_final_fixed.md`
3. Minimal review outputs:
   - `Outputs/reports/run_latest.json` (overwrite)
   - `Outputs/reports/runs.jsonl` (append-only, dedup by run_id)
4. Verification commands documented (and runnable) for:
   - NW2 completeness check (existing script)
   - NW4 authoritative validation (existing script)
5. Windows minimal UX wrapper (distribution-ready):
   - `GermanNewWords.exe` + `GermanNewWords.runtime/` (initially console-first)
   - writes `Outputs/logs/run_latest.log`
   - optionally auto-opens `Outputs/06_words_final_fixed.md` on success

## 3) Task/Wave Breakdown

### Task 0 — Baseline inventory + constraints lock

Steps
- Locate/inspect existing tooling entrypoints in `Tools/` (mdproc + scripts).
- Identify how NW1–NW4 currently executed (manual sequence) and map to pipeline stages.
- Extract any existing tag mapping / allowlist logic from mdproc (avoid re-implementing differently).

Verification
- Record inventory notes in `Outputs/reports/run_latest.json` under `env` (versions, tool paths).

### Task 0.5 — UX contract alignment (CLI + .exe wrapper)

Steps
- Lock canonical user workflow for non-CLI users:
  - double-click `.exe` runs full pipeline
  - interactive NotebookLM auth may open Chrome when required
- Decide packaging approach:
  - console-first `.exe` (PyInstaller) as baseline
  - GUI deferred (explicit non-goal for initial release)
- Define log contract:
  - `Outputs/logs/run_latest.log` overwrite per run
  - keep existing `Outputs/reports/*` trend artifacts (optional for end users, but useful for support)

Verification
- Update plan assumptions section (this plan) and confirm spec section 4.7 is satisfied.

### Task 1 — SSOT data model layer (Pydantic)

Steps
- Create Pydantic models:
  - `VocabEntry`
  - `SeeAlsoRef`
  - `FinalVocabDatabase`
  - `Violation`, `RuleId`, `ReviewResult`
- Encode invariants that are truly structural (types, required fields, hygiene constraints).

Symmetry/invariance enforcement
- Single `Violation` schema used by:
  - deterministic validators
  - LLM QA reviewer
  - tool output parsing

Verification
- Add small unit-style checks (if repo has test harness) OR minimal script to instantiate/validate models with known-good and known-bad fixtures.

### Task 2 — SSOT deterministic validators + normalizers (NW1–NW4)

Steps
- Implement idempotent normalizers:
  - vocab field cleanup (NW2)
  - see_also cleanup (NW4)
- Implement deterministic validators as composition of rule checks:
  - NW1 anti-placeholder denylist (as RuleChecks, not in nodes)
  - NW1 `word:` hygiene rules
  - NW3 merge invariants (dedupe, ordering) at merge stage
  - NW4 canonical see_also structure + noun consistency checks

Symmetry/invariance enforcement
- No node-specific validation logic; nodes call `validate_*` only.
- Normalizers must be pure + idempotent.

Verification
- Run validators against sample blocks (extract a few from current `Outputs/*.md`) and confirm stable outputs after repeated normalization.

### Task 3 — LLM quality review gate (NW1 QA)

Steps
- Define PydanticAI reviewer agent that outputs `ReviewResult`.
- Convert `ReviewResult` into `Violation[]` using same schema.
- Add evidence requirement:
  - every `fail` issue includes substring evidence from offending field.

Verification
- Create fixture with mixed-language `de_1` (English + German) and confirm reviewer flags `mixed_language_de1`.
- Confirm deterministic denylist still applied before LLM QA.

### Task 4 — NotebookLM MCP adapter + batch planner (bottleneck fix)

Steps
- Implement NotebookLM MCP wrapper:
  - strict per-call timeout (MCP `browser_options.timeout_ms`)
  - hard stage wall-clock budget
  - structured JSON-only prompt enforcement
  - Pydantic schema validation of tool output
- Implement batch planner (AIMD):
  - start `B0=20`, `B_max=60`, `B_min=1`
  - success => increase; timeout => halve
  - retry/backoff/jitter; split on repeated failure
  - requeue only missing words
- Implement circuit breaker:
  - N consecutive timeouts => reset session; shrink batch; fail stage if persists

Verification
- Dry-run adapter against small word list (5–10) and confirm:
  - timeouts enforced (no hang)
  - partial results requeued only for missing
  - batch size history captured in `run_latest.json`

### Task 5 — LangGraph graph implementation (thin nodes)

Steps
- Define `PipelineState` (Pydantic) capturing:
  - inputs, entries, unresolved, violations, retry counts
  - tool telemetry + batch sizing state
  - report accumulator
- Implement nodes as orchestration only:
  - preprocess/classify/sort/dedupe
  - enrich entry (PydanticAI)
  - deterministic validate/normalize
  - LLM QA review (optional gate)
  - see_also tool node + parse/validate + requery loop
  - merge see_also + final NW4 normalize/validate
- Use shared quality-gate harness for all loops.

Symmetry/invariance enforcement
- One retry policy module; configured per gate, not hardcoded in nodes.
- One merge implementation; no duplicated “dedupe keep-first” logic in multiple places.

Verification
- Run pipeline on existing `Inputs/Word List (DE).md` and confirm 7 md outputs created/overwritten.

### Task 6 — Output writers + minimal review artifacts (low noise)

Steps
- Implement Markdown exporter from `FinalVocabDatabase` to required md surfaces:
  - keep filenames stable (overwrite)
  - ensure NW3 placement rule on export
- Implement run reporting:
  - compute `run_id` from inputs hash + prompt versions + code version
  - write `Outputs/reports/run_latest.json` overwrite
  - append `Outputs/reports/runs.jsonl` only if new run_id
  - store only top N fail examples in `run_latest.json`

Verification
- Run twice with unchanged inputs and confirm:
  - md files overwritten (same names)
  - `runs.jsonl` not duplicated for same run_id

### Task 7 — End-to-end verification + handoff

Steps
- Run existing validators where available:
  - `python Tools/scripts/validate_word_list.py` (NW2 Step 0 analog)
  - `python Tools/scripts/validate_requirement4.py` (NW4 authoritative)
- Compare counts:
  - word list count vs entry blocks count (minus unresolved)
- Capture final metrics row in `runs.jsonl`.

Verification
- Evidence artifacts:
  - `Outputs/06_words_final_fixed.md`
  - `Outputs/reports/run_latest.json`
  - `Outputs/reports/runs.jsonl`
  - validator console output (captured in run logs or copied into report fields)

### Task 8 — Build Windows .exe wrapper (minimal UX)

Steps
- Implement a thin application entrypoint that:
  - checks `Inputs/Word List (DE).md`
  - ensures NotebookLM auth (launches interactive auth only if needed)
  - runs pipeline through NW4
  - writes `Outputs/logs/run_latest.log`
  - prints final success path and optionally auto-opens `Outputs/06_words_final_fixed.md`
- Package as console-first `.exe`:
  - bundle Python runtime + dependencies into `GermanNewWords.runtime/`
  - emit `GermanNewWords.exe`
- Ensure wrapper does not duplicate pipeline logic:
  - wrapper calls same pipeline runner entrypoint and SSOT modules

Verification
- Smoke test:
  - double-click `.exe` (or run from cmd) produces same outputs as CLI path
  - if auth expired, Chrome opens, then run continues
- Evidence:
  - `Outputs/logs/run_latest.log` exists and contains step boundaries + failures

## 4) Verification (top-level)

Commands (expected in repo root)
- NW2 completeness gate:
  - `python Tools/scripts/validate_word_list.py`
- NW4 authoritative validation:
  - `python Tools/scripts/validate_requirement4.py`

Success signals
- NW4 validator passes for `Outputs/06_words_final_fixed.md`
- No hangs in NotebookLM stage; timeouts enforced; missing words requeued; circuit breaker behaves
- `runs.jsonl` shows stable metric keys and trendable values
- `.exe` wrapper produces identical outputs and writes `Outputs/logs/run_latest.log`

## 5) Rollback / Safety

- If pipeline output quality regresses:
  - disable LLM QA gate via config (keep deterministic)
  - pin batch size to conservative `B0=B_min` temporarily
- If NotebookLM MCP auth breaks:
  - run MCP `re_auth` / `setup_auth` (outside pipeline), then retry
