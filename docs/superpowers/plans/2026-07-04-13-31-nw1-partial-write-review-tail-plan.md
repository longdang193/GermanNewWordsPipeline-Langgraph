---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: nw1-partial-write-review-tail
parent_thread: current-thread
parent_spec: docs/superpowers/specs/2026-07-04-00-00-nw1-de1-sentence-and-target-realization-spec.md
targets:
  - docs/superpowers/specs/2026-07-04-00-00-nw1-de1-sentence-and-target-realization-spec.md
  - Tools/scripts/process_requirement1.py
  - Tools/src/gnw_pipeline/nw1_qa.py
  - Tools/scripts/nw1_qa_review.py
  - Tools/scripts/run_full_pipeline.py
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

Legacy note: filename and `name` still say `review-tail`, but authoritative contract terms in this plan are `clean | unresolved_part | omitted`.

# Goal

Stop NW1 from failing all-or-nothing when some terms miss generation-time QA, by writing every unresolved entry that still has valid block schema at the tail of `Outputs/01_words.md`, preserving block schema for NW3/NW4, and keeping only structurally unusable entries out of the main artifact.

# Scope

- In scope: partial-write behavior in `process_requirement1.py`, explicit output statuses for NW1 term resolution, tail placement for unresolved blocks, true blocker reporting, automatic NW3/NW4 continuation gate, and focused regression tests.
- In scope files are limited to `Tools/scripts/process_requirement1.py`, `Tools/src/gnw_pipeline/nw1_qa.py`, `Tools/scripts/nw1_qa_review.py`, `Tools/tests/test_process_requirement1_failure_contract.py`, and `Tools/tests/test_validation_core.py`.
- Out of scope: new repair loop, new LLM pass, NW2–NW4 contract rewrite, corpus filtering pipeline, or generic workflow engine.

# Diagnosis

- Current NW1 already writes usable output before raising on omitted terms.
- Current unresolved summary still mixes fallback-origin labels like `missing_meaning` with later true blockers like `target_not_realized`.
- Current pipeline runner still treats NW1 non-zero as terminal even when `Outputs/01_words.md` contains parseable blocks.
- Result: one handful of hard terms prevents automatic NW3/NW4 continuation even when most entries are usable and parseable.

# Resolution Contract

1. NW1 must always write `Outputs/01_words.md` when at least one valid block was produced.
2. Generation outcomes must split into exactly three statuses:
   - `clean`
   - `unresolved_part`
   - `omitted`
3. `unresolved_part` means block is structurally valid, is not accepted as clean, and needs later human or QA attention.
4. `omitted` means block could not be serialized into required NW1 shape and must stay out of file.
5. Any unresolved entry with valid block schema must no longer be omitted by default; it must route serialized block to `unresolved_part`.
6. Structural block failures still remain fatal at entry level.
7. Unified QA report rows must preserve both:
   - origin reason code
   - final blocker code
   - resolution status
8. Exact tail marker must be `## UNRESOLVED PART`.
9. Tail entries must remain normal `SSTART...EEND` blocks; no second machine-readable schema may be introduced inside output blocks.
10. Write file whenever at least one `clean` or `unresolved_part` block exists.
11. Return non-zero only when `omitted` is non-empty.
12. `run_full_pipeline.py` must continue to NW3/NW4 when `Outputs/01_words.md` exists and contains at least one parseable block, even if NW1 exits non-zero due to omitted entries.

# Key Deliverables

1. One spec patch that brings unresolved-part tail behavior in-bounds before code changes.
2. One entry-status model in `process_requirement1.py` that separates `clean`, `unresolved_part`, and `omitted` by block-schema validity plus acceptance outcome.
3. One output writer that writes clean blocks first and unresolved-part blocks after a stable tail marker.
4. One unified QA-report contract that records unresolved status and true blocker cause without breaking block schema.
5. One focused regression suite proving partial write, tail placement, deterministic ordering, downstream block parse compatibility, omitted-only hard stop behavior, and NW3/NW4 continuation gate.
6. One runner patch that uses shared block parsing instead of raw NW1 exit code as the only continuation gate.

# Task Breakdown

## Task 0 — Patch spec scope first

**Files**
- `docs/superpowers/specs/2026-07-04-00-00-nw1-de1-sentence-and-target-realization-spec.md`

**Work**
- Patch current parent spec before code work.
- Bring unresolved-part tail behavior explicitly in-bounds.
- Replace report-only/downstream-unchanged language where it conflicts with tail placement.
- Add exact exit-code and marker-contract expectations.

**Verification**
- Spec no longer contradicts tail-write implementation.
- Acceptance criteria mention repo output write with unresolved-part blocks and downstream continuation gate.

## Task 1 — Split entry outcomes by writeability

**Files**
- `Tools/scripts/process_requirement1.py`

**Work**
- Inspect `_resolve_entry_candidate(...)`, `validate_entry_quality(...)`, and `process()` as one flow.
- Keep fallback-origin reason codes, but add final status classification after QA and serialization outcome are known.
- Use smallest possible model, likely dicts or tiny tuples, not new class hierarchy.
- Rules, in exact precedence order:
  - accepted final serialized `entry` exists -> `clean`
  - unaccepted entry has any valid serialized `SSTART...EEND` block -> `unresolved_part`
  - no valid serialized block exists -> `omitted`
- Define `valid serialized block` concretely as block text that survives `mdproc.validation_core.iter_blocks(...)` and block-level NW1 field parsing.
- Keep soft-review issues non-blocking and out of fatal path unless generation-time acceptance explicitly rejects them.

**Verification**
- One term with `target_not_realized` but valid block routes to `unresolved_part`.
- One failed-repair term with remembered last valid block routes to `unresolved_part`.
- One term with no block still routes to `omitted`.
- No all-or-nothing raise occurs when only `unresolved_part` items exist.
- Exit code stays `0` when only `clean` and `unresolved_part` blocks exist.
- Exit code is non-zero when `omitted` is non-empty.

## Task 2 — Write clean body plus review tail

**Files**
- `Tools/scripts/process_requirement1.py`

**Work**
- Update `write_entries(...)` to accept two entry lists:
  - clean body entries
  - unresolved-part entries
- Keep all blocks valid `SSTART...EEND` blocks.
- Add exact tail section header: `## UNRESOLVED PART`.
- Do not add second machine-readable unresolved schema in block comments.
- Do not invent a second output file unless absolutely needed.
- Preserve original relative order within clean section and within unresolved-part section.

**Verification**
- Output file is written when clean or unresolved-part entries exist.
- Unresolved-part blocks appear after stable section header.
- Existing summary comments remain parseable.
- Clean blocks preserve input order.
- Unresolved-part blocks preserve input order relative to each other.

## Task 3 — Surface true blocker reason

**Files**
- `Tools/scripts/process_requirement1.py`
- `Tools/scripts/nw1_qa_review.py`
- `Tools/src/gnw_pipeline/nw1_qa.py`

**Work**
- Keep current origin labels such as `missing_meaning` and `missing_de_example`.
- Add final blocker fields where applicable, for example:
  - `origin_reason_code`
  - `final_blocker_code`
- For LLM-repaired blocks that serialize but fail QA, store exact hard-fail codes from `qa_entry_issues(...)`.
- For omitted entries, keep current unresolved summary but make blocker source truthful.
- Keep machine-readable unresolved metadata only in unified QA report rows, not block comments.
- Reuse current SSOT issue codes; do not mint synonyms.
- When LLM repair fails after producing one or more valid candidate blocks, keep the last valid serialized block and route it to `unresolved_part`.
- Make that storage contract explicit in code path: retry flow retains last valid serialized candidate block per term until `_resolve_entry_candidate(...)` classifies final status.
- Add row fields at minimum:
  - `resolution_status`
  - `origin_reason_code`
  - `final_blocker_code`
  - `written_to_output`

**Verification**
- `an die + Zahl` reports fallback origin plus final blocker `target_not_realized` when applicable.
- `umsehen` reports verb blocker truthfully rather than generic missing fallback label alone.

## Task 4 — Continue runner when parseable blocks exist

**Files**
- `Tools/scripts/run_full_pipeline.py`

**Work**
- Reuse `mdproc.validation_core.iter_blocks(...)` as SSOT parser for continuation gating.
- Continue to NW3/NW4 when `Outputs/01_words.md` exists and yields at least one parseable block.
- Stop only when NW1 produced no parseable blocks or no file.
- Do not add second parser or second readiness heuristic.

**Verification**
- One focused runner test proves NW3/NW4 continue after NW1 non-zero with usable output.
- One focused runner test proves stop when file missing or zero parseable blocks.

## Task 5 — Add focused regressions for partial write behavior

**Files**
- `Tools/tests/test_process_requirement1_failure_contract.py`
- `Tools/tests/test_validation_core.py`
- runner-focused test file covering `run_full_pipeline.py`

**Work**
- Add one regression proving run writes file when at least one entry is clean and another is unresolved-part.
- Add one regression proving unresolved-part block lands after section header.
- Add one regression proving truly omitted entries still stay out of output.
- Add one regression proving report metadata keeps both origin and final blocker cause.
- Add one regression proving mixed clean/unresolved-part ordering is deterministic.
- Add one small downstream parse smoke test proving section header and comment metadata do not break NW3/NW4-style block iteration.
- Add one small pipeline-runner test proving NW3/NW4 continue when parseable blocks exist despite NW1 non-zero.
- Add one regression proving failed-repair entry with last valid block lands in `## UNRESOLVED PART`.
- Add one regression proving count reconciliation invariant: `clean + unresolved_part + omitted == processed - skipped`.
- Keep tests small and repo-local; no live-run dependency.

**Verification**
- Red-green cycle proves old all-or-nothing behavior changed only where intended.
- Focused tests distinguish `unresolved_part` from `omitted`.
- Downstream block parser still reads all written blocks with section header present.
- Focused tests prove soft-review-only entries remain clean unless explicit acceptance rejects them.

## Task 6 — Optional smoke rerun on known live input

**Files**
- no new source target beyond existing scripts and outputs

**Work**
- Keep repo-local tests as approval gate.
- If extra confidence is wanted, rerun NW1 with same approved external input source and repo output root.
- Confirm repo output file gets written even when some terms remain omitted.
- Confirm downstream runner continues to NW3/NW4 when file has parseable blocks.
- Inspect whether target problem terms still produce valid improved `de_1`.

**Verification**
- Optional smoke only: `Outputs/01_words.md` exists after run.
- Optional smoke only: `## UNRESOLVED PART` exists when unresolved serialized entries occur.
- Optional smoke only: omitted summary names remaining dropped terms separately.

# Validation Rules

- Structurally valid block must never be omitted solely because of deterministic QA hard-fail on content quality.
- Structurally invalid or unserializable entry must never be written into canonical NW1 output.
- `process_requirement1.py` must not invent duplicate QA logic; it only consumes SSOT QA results.
- Same issue codes remain authoritative in `nw1_qa.py`.
- Partial-write behavior must preserve deterministic ordering of entries.
- `run_full_pipeline.py` must use `mdproc.validation_core.iter_blocks(...)` for continuation gating.
- `clean + unresolved_part + omitted` must reconcile to `processed - skipped` for every run.

# Risky Migrations

- Tail blocks may confuse downstream consumers if they assume every block is equally clean.
- Changing unresolved metadata location can break consumers if they read block comments instead of unified QA rows.
- Reclassifying content issues into unresolved-part can hide too much if structural vs quality boundaries are sloppy.

# Best Lazy Implementation

- Reuse existing serialized block text.
- Add one tiny status split in `process()`.
- Keep one output file.
- Keep one plain section header.
- Reuse existing shared block parser in runner gate.

# Verification

- `py -m pytest Tools/tests/test_process_requirement1_failure_contract.py -q`
- `py -m pytest Tools/tests/test_validation_core.py -q`
- focused runner test command covering `run_full_pipeline.py`
- optional smoke: rerun NW1 with approved external input source and repo output root

# Precondition Note

Current parent spec used review-tail + JSON-tail language. Before implementation starts, patch spec scope and acceptance criteria so unresolved-part block-tail behavior and downstream continuation gate are explicitly in-bounds.
