---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: german-listening-mvp-4layer-spec
parent_workstream: none
targets:
  - C:/Users/HOANG PHI LONG DANG/repos/German_Listening
related_features:
  - mvp_3_action_flow
  - langgraph_orchestration
  - hitl_in_block_creation
  - packaging_and_exe
  - action1_mode_router
related_stages:
  - app_flow
  - live_run
  - verify
  - package
---

# Goal
Build `German_Listening` MVP in `German_NewWords` style: LangGraph orchestrates outputs, HITL lives in app, product flow fixed to exact 3 actions, and Action 1 uses mode router that preserves SSOT, symmetry, invariance.

# Product Flow Layer (Primary)
## Exact 3-Action Contract
Main menu must show only:
1. `CREATE LISTENING BLOCKS for ANKI`
2. `CREATE AUDIOS and TRANSCRIPTS from CREATED LISTENING BLOCKS`
3. `EXIT`

## Action 1 Contract: CREATE LISTENING BLOCKS for ANKI
Prompt user for:
- transcript path
- audio path
- mode: `marker-based | classic-based | agent suggestions`
Then run block creation.

Output:
- `Outputs/Listening-generated.md`

### Action 1 Mode Router Contract
- Router computes transcript profile SSOT (`marker_capable`, `classic_capable`, `reason`).
- `marker-based`: run marker pipeline only when `marker_capable=true`; otherwise typed fail with fallback guidance.
- `classic-based`: run classic pipeline.
- `agent suggestions` (HITL super-mode):
  - route marker when `marker_capable=true`
  - route classic/semantic fallback when marker is not available
  - always enter HITL decision surface (accept/regenerate/discard/manual), unless hard parse failure.
- Router must write run record with requested mode and routed mode.

## Action 2 Contract: CREATE AUDIOS and TRANSCRIPTS from CREATED LISTENING BLOCKS
Input: existing listening blocks file (default `Outputs/Listening-generated.md`).

Behavior:
- if file missing: prompt user with only
  1. create new listening blocks now
  2. exit
- if file exists: run deterministic split/subtitle generation

Output:
- `Outputs/Youtube/*.mp3`
- `Outputs/Youtube/*.srt`

## Action 3 Contract: EXIT
- terminate app safely

# Pipeline/Runtime Layer
1. LangGraph is primary orchestration path for runtime pipeline execution.
2. Marker pipeline order invariant: `generate -> suggest_boundaries -> apply_boundaries -> enrich_llm -> quality_gate -> validate -> split`.
3. `suggest_boundaries` is LLM-assisted boundary scoring node under hard timing guardrails.
4. Boundary selector hard constraints: sentence-boundary cuts only, prefer ~45s, allow natural-short conversational unit, never exceed 60s.
5. Uncertain boundary decisions in `agent suggestions` mode must expose HITL options: accept, regenerate, discard/manual.
6. Validation gate invariant: split cannot run after validation fail.
7. Deterministic split/subtitle logic remains deterministic (`ffmpeg` + timestamps).

# Packaging Layer
1. CLI app must expose equivalent menu-driven flow.
2. `exe` packaging is supported but is only one delivery part.
3. Packaging docs and runtime instructions must work for both script and exe forms.

# Evidence/Operations Layer
1. Store verification artifacts under `docs/superpowers/plans/evidence/`.
2. Required evidence:
- menu flow proof (action 1/2/3)
- marker validator PASS
- block/mp3/srt equality proof
- HITL decision log evidence
- boundary scoring evidence (candidate scores, selected cuts, confidence)
- mode router evidence (requested mode, routed mode, profile, outcome)
- classic deferred note (if classic not closed)

# SSOT, Symmetry, Invariance
## SSOT (Single Source of Truth)
1. Transcript path and audio path selected in Action 1 are canonical inputs for that run.
2. Transcript profile output is canonical router input for Action 1 routing decisions.
3. Created listening blocks markdown is canonical source for Action 2 deterministic outputs.
4. Taxonomy file (`configs/labels.toml`) is canonical source for allowed HITL labels.
5. Boundary suggestion artifacts are canonical evidence for semantic split decisions.
6. Requirement wrappers are compatibility surfaces only; package layer is logic owner.

## Symmetry
1. Action 1 modes share one uniform request/response contract: same prompts, same output artifact path, same report shape.
2. `agent suggestions` must not depend on marker-only preconditions; it must route by profile and remain functional for non-marker transcripts.
3. Action 2 deterministic generation treats each block identically (`one block -> one mp3 + one srt`) regardless of mode origin.

## Invariance
1. Menu invariance: app shows only 3 top-level actions.
2. Gate invariance: split cannot run without valid listening blocks source.
3. Count invariance: successful Action 2 requires `blocks == mp3 == srt`.
4. Validation invariance: fail state blocks downstream side effects.
5. Boundary invariance: no selected block exceeds 60 seconds.
6. Router invariance: no marker pipeline call when transcript profile is not marker-capable.

# Key Deliverables
1. 3-action app flow implemented exactly.
2. Action 1 supports path inputs and 3 modes including HITL suggestions mode.
3. Action 1 mode router implemented with profile-based routing and run record artifact.
4. Action 2 deterministic behavior with missing-file branch prompt.
5. LangGraph orchestration active for output-producing runs with `suggest_boundaries` and `apply_boundaries` nodes.
6. HITL decisions are logged to JSONL in app flow.
7. Packaging (including exe) documented as secondary delivery layer.

# Acceptance Criteria
1. User can complete action 1 with explicit transcript/audio/mode inputs.
2. `agent suggestions` works on marker and non-marker transcripts via router.
3. Marker mode on non-marker transcript fails with typed routing message, not deep pipeline crash.
4. Action 2 missing-file branch prompts exactly `create new` or `exit`.
5. Action 2 on valid blocks produces deterministic outputs and count parity.
6. Marker validator reports PASS for generated marker run.
7. Boundary suggestions are present and constrained to timing contract (`<=60s`, target `30–60s`, sweet spot `~45s`).
8. HITL mode in action 1 records at least one decision event (including boundary review when uncertainty threshold triggered).
9. Packaging layer includes runnable CLI and documented exe build path.

# Non-Goals
1. Closing classic parity in this MVP unless explicit additional approval.
2. Multi-agent autonomous content generation.

# Validation Plan
- proof target: 3-action menu contract
  - method: run app and capture interaction transcript
  - evidence: menu/options + branch behavior logs
- proof target: action 1 router behavior
  - method: run action 1 with marker transcript and non-marker transcript under `agent suggestions`
  - evidence: run record artifact showing routed mode and outcome
- proof target: boundary suggestion node compliance
  - method: run marker flow with suggestion logging enabled
  - evidence: boundary scoring JSONL + selected boundary summary + uncertainty/HITL branch proof
- proof target: action 2 deterministic outputs
  - method: run split flow
  - evidence: mp3/srt files + count proof
- proof target: marker compliance
  - method: run `check_listening_4.py`
  - evidence: PASS snapshot
- proof target: HITL in app
  - method: run agent suggestions path
  - evidence: labels JSONL tail + boundary HITL log tail

# Completion Criteria
1. All 3 actions work as specified.
2. Marker branch verified end-to-end.
3. Agent suggestions branch verified for marker and non-marker inputs.
4. Evidence bundle complete across all 4 layers.
5. Classic status explicitly documented (complete or deferred).
