---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: nw1-de1-sentence-and-target-realization
parent_workstream: none
targets:
  - Tools/scripts/process_requirement1.py
  - Tools/src/gnw_pipeline/nw1_qa.py
  - Prompt/nw1_enrich_instructions.md
  - Tools/scripts/nw1_qa_review.py
  - Tools/scripts/run_full_pipeline.py
  - Tools/src/gnw_pipeline/langgraph_app.py
  - Tools/tests/test_process_requirement1_failure_contract.py
  - Tools/tests/test_validation_core.py
---

# Spec: NW1 `de_1` sentence-shape and target-realization contract

## Note (canonical template gap)

Repo currently lacks canonical `docs/operating_system/...` template files referenced by skills. This spec follows required section set and existing repo spec shape.

## Triage

Layer: change  
Feature type: MODIFY  
Summary: align NW1 generation-time acceptance and always-run deterministic QA so sentence fragments and lexeme-miss examples are blocked before output and still reported consistently  
Affected stages: NW1  
Affected features: nw1-generation, nw1-qa  
Spec needed: yes  
Plan needed: yes

## 1) Goal

Define concrete NW1 validation rules for `de_1` so that:
- sentence fragments like `voller Leidenschaft und mit ganzem Einsatz` do not silently pass
- paraphrases like `ein freundlicher, fürsorglicher Ort` do not pass for target `eine warme Umgebung`
- explicit stored verb forms, including separable verb forms already present on entries, can be recognized when sentence truly uses target lexeme
- invalid LLM-repaired examples are rejected during generation-time acceptance before they reach `Outputs/01_words.md`
- tricky cases are still reported in one machine-readable QA artifact instead of causing ambiguous ad hoc behavior

## 2) Key Deliverables

1. One deterministic `de_1` sentence-shape validator.
2. One deterministic `de_1` target-realization validator.
3. One SSOT `QaIssue` / `QaReportRow` schema owned by `Tools/src/gnw_pipeline/nw1_qa.py`.
4. One generation-time acceptance gate in `Tools/scripts/process_requirement1.py` that reuses SSOT deterministic `de_1` QA.
5. One tightened `Prompt/nw1_enrich_instructions.md` contract for full-sentence and target-realization output.
6. One always-run deterministic NW1 QA report step in both CLI pipeline paths.
7. One severity split: `hard_fail | soft_review` per issue.

## 3) Task/Wave Breakdown

### Wave A — Deterministic sentence-shape contract
- Add sentence-shape checks for `de_1`.
- Keep rules cheap, deterministic, and evidence-producing.
- Reject obvious fragments without parser dependency.

### Wave B — Deterministic target-realization contract
- Add tag-aware lexical-realization checks.
- Support phrase/noun/adjective/adverb realization with normalization.
- Support verb realization from explicit stored forms already present on entry data.

### Wave C — SSOT issue/report schema
- Define one issue/report schema in `nw1_qa.py`.
- Make deterministic QA and optional LLM QA emit same row shape.
- Keep field names stable across CLI and LangGraph paths.

### Wave D — Generation-time enforcement
- Reuse SSOT deterministic `de_1` QA during NW1 LLM-repair acceptance.
- Reject repaired entries on `hard_fail` issues before final output write.
- Keep retry behavior bounded and deterministic.

### Wave E — Pipeline wiring
- Run deterministic NW1 QA after NW1 validation in `run_full_pipeline.py`.
- Run deterministic NW1 QA after NW1 validation in `langgraph_app.py`.
- Deterministic QA exits `0` by default and writes report artifact.
- Optional LLM review remains opt-in and non-mutating.

## 4) Design Decisions

### 4.1 Two distinct `de_1` quality questions

`de_1` quality splits into two independent checks:
1. `looks_like_sentence`
2. `realizes_target_lexeme`

Both must be validated. A sentence may be grammatical enough but still fail because target lexeme never appears. A sentence may mention target lexeme but still fail because it is only a fragment.

### 4.2 Sentence-shape contract

Deterministic sentence-shape rules:
- hard fail if `de_1` does not end with `.`, `!`, or `?`
- hard fail if `de_1` ends with `,`, `;`, or `:`
- hard fail if fewer than 3 word tokens remain after trimming punctuation
- soft review if first alphabetic character is lowercase
- soft review if no likely predicate cue is found

Likely predicate cue means one of:
- stored verb form appears in entry metadata
- common finite/copula/modal helper appears in sentence, for example `ist`, `sind`, `war`, `waren`, `hat`, `haben`, `wird`, `werden`, `kann`, `können`, `muss`, `müssen`, `soll`, `sollen`, `will`, `wollen`, `darf`, `dürfen`
- small shared lexical list covers common high-frequency predicates such as `geht`, `kommt`, `liegt`, `steht`, `bleibt`, `gibt`, `macht`, `braucht`

Rationale:
- missing punctuation is safe hard-fail evidence
- exact finite-verb parsing is too brittle for first pass
- no-predicate cases should be reviewed, not blindly accepted

Concrete examples:
- `voller Leidenschaft und mit ganzem Einsatz` -> hard fail: missing terminal punctuation; soft review: no predicate cue
- `Voller Leidenschaft und mit ganzem Einsatz.` -> soft review: no predicate cue
- `Er arbeitet voller Leidenschaft und mit ganzem Einsatz.` -> pass

### 4.3 Target-realization contract

`de_1` must realize target lexeme, not merely paraphrase meaning.

Realization means deterministic proof that example sentence uses target lexical item directly, with allowed normalization by tag.

The validator must not accept semantic paraphrase alone.

Concrete example:
- target `eine warme Umgebung`
- bad `ein freundlicher, fürsorglicher Ort`
- result: `target_not_realized`

### 4.4 Normalization for noun/adjective/adverb/phrase realization

Shared normalization rules:
- lowercase for comparison only
- normalize whitespace to single spaces
- strip surrounding punctuation from tokens
- preserve token order
- for phrase-like multi-token targets, require one contiguous normalized span match unless verb split-form rules explicitly apply
- drop German articles for coverage matching: `der`, `die`, `das`, `ein`, `eine`, `einer`, `einem`, `einen`
- allow light adjective-ending folding for common attributive forms:
  - `warme`, `warmen`, `warmer`, `warmes`, `warmem` -> `warm`
- do not introduce full lemmatizer in first version

One authoritative `match_mode` must be derived once per entry inside `nw1_qa.py`. Validation must branch on `match_mode`, not on ad hoc tag exceptions in multiple places.

Initial `match_mode` rules:
- `phrase_contiguous_surface` for multi-token phrase-like targets such as `eine warme Umgebung`
- `single_token` for ordinary adjective/adverb targets
- `noun_surface` for noun entries whose canonical noun identity is single lexical noun or stable article-led noun phrase
- `verb_explicit_forms` for verb entries with `word_inf` and stored verb forms

Concrete examples:
- target `eine warme Umgebung` -> normalized content target `warm umgebung`
- `Kinder brauchen eine warme Umgebung.` -> pass
- `In so einer warmen Umgebung fühlen sich Pflanzen wohl.` -> pass
- `ein freundlicher, fürsorglicher Ort` -> `target_not_realized`

### 4.5 Verb realization contract

Verb entries use lexical-form matching, not semantic paraphrase.

Accepted proof sources, in priority order:
1. explicit forms already stored on entry:
   - `word_inf`
   - `verb_present`
   - `verb_past`
   - `verb_perfect`
2. clause-local split matching derived only from stored split forms already present on the entry
3. optional LLM review only when deterministic proof is inconclusive

Rules:
- unsplit infinitive match passes: `aufgeben`
- stored present-form match passes: `Er greift sofort zu.` for stored form `greift zu`
- stored past-form match passes: `Er griff sofort zu.` for stored form `griff zu`
- perfect-form match passes: `Er hat schon aufgegeben.`
- for stored split forms like `greift zu`, split match is allowed only when:
  - first token matches stored finite verb token
  - particle matches stored particle token
  - both appear in same clause
  - no clause punctuation `, ; : . ! ?` appears between them
- do not infer unstored conjugations in first version
- do not accept distant cross-clause token coincidences as proof

Rationale:
- repo already stores explicit split-friendly forms for entries such as `zugreifen`
- full German conjugation generation is out of scope
- same-clause split proof is less arbitrary than fixed token-gap heuristics

### 4.6 Severity model

Issue classes:
- `hard_fail`: deterministic, high-confidence violation
- `soft_review`: ambiguous or parser-level uncertainty

Initial severity mapping:
- missing terminal punctuation -> `hard_fail`
- bad terminal punctuation -> `hard_fail`
- fewer than 3 tokens -> `hard_fail`
- phrase/noun/adj/adv target not realized after normalization -> `hard_fail`
- explicit verb-form target not realized -> `hard_fail`
- no predicate cue -> `soft_review`
- lowercase sentence start -> `soft_review`
- verb realization inconclusive because sentence may use unstored conjugation -> `soft_review`

### 4.7 Ownership and mutation boundaries

Ownership is explicit:
- `nw1_qa.py` owns deterministic QA logic, match-mode derivation, issue/report schema, and optional LLM-review row normalization
- `nw1_qa.py` also owns one shared entry-block parser or constructor used to build `QaEntry` consistently across generation-time and report-time callers
- `nw1_qa_review.py` owns file scan, row collection, and report writing only
- `run_full_pipeline.py` and `langgraph_app.py` own step ordering only
- `process_requirement1.py` may invoke SSOT deterministic QA during generation-time acceptance, but must not own a second parser or duplicate QA policy
- `Prompt/nw1_enrich_instructions.md` owns LLM output instructions, not acceptance policy

Mutation boundary:
- generation-time acceptance may reroute candidate repaired entries into clean, unresolved-part, or omitted buckets before write
- QA/reporting logic outside NW1 generation must not rewrite `Outputs/01_words.md`
- NW1 generation may write unresolved-part blocks to `Outputs/01_words.md` in this patch
- optional LLM review may add report rows, but may not mutate source blocks in this patch

### 4.8 Run-level behavior

Structural NW1 failures remain fatal:
- malformed blocks
- missing required fields
- placeholder text
- existing path-drift behavior remains unchanged and is out of scope

Semantic `de_1` QA behavior in this spec:
- generation-time deterministic QA may reroute repaired entries with `hard_fail` issues into an unresolved-block tail in `process_requirement1.py`
- deterministic QA always runs after NW1 structural validation in both pipeline entrypoints
- deterministic QA writes machine-readable report and exits `0` by default
- optional LLM review remains env/config gated and non-blocking
- unresolved semantic issues are still reported with truthful blocker metadata in this patch
- downstream NW3/NW4 continuation must depend on written parseable block count, not only on NW1 exit code

This patch intentionally chooses minimal symmetric partial-write behavior: route every unresolved entry with valid `SSTART...EEND` block schema into an unresolved-block tail, keep only structurally unusable entries out of file, and preserve one stable block contract for NW2–NW4.

### 4.9 SSOT issue/report schema

One authoritative report schema must be defined in `nw1_qa.py`.

Minimum `QaIssue` fields:
- `code`
- `field`
- `severity`
- `message`
- `evidence`
- `source` = `deterministic` | `llm`

Minimum required deterministic issue codes:
- `missing_terminal_punctuation`
- `bad_terminal_punctuation`
- `too_few_tokens`
- `sentence_starts_lowercase`
- `no_predicate_cue`
- `target_not_realized`
- `verb_realization_inconclusive`

Minimum `QaReportRow` fields:
- `word`
- `word_inf`
- `start_line`
- `end_line`
- `issues`

Top-level report payload must include:
- `input`
- `rows`
- `row_count`
- `issue_count`
- `env`

For generation-time unresolved handling, the same unified `rows` report is the SSOT machine-readable artifact for:
- `resolution_status`
- `origin_reason_code`
- `final_blocker_code`
- unresolved-part vs omitted status
- omitted-entry identity

Minimum row-level unresolved fields:
- `resolution_status` = `clean` | `unresolved_part` | `omitted`
- `origin_reason_code`
- `final_blocker_code`
- `written_to_output`

No second unresolved metadata schema may be introduced in block comments or sidecar JSON.

Output tail contract for `Outputs/01_words.md` must include exact marker:
- `## UNRESOLVED PART`

No machine-readable per-block metadata is required inside `Outputs/01_words.md` beyond stable section placement. Block body schema itself must remain unchanged.

Tail membership rule is shape-based, not issue-cause-based:
- if entry has valid `SSTART...EEND` block schema but is not accepted into clean output, it must be placed in `## UNRESOLVED PART`
- if entry cannot be serialized into valid block schema, it must be omitted

For this patch, `valid block schema` means one serialized block text that:
- is readable by `mdproc.validation_core.iter_blocks(...)`
- preserves canonical NW1 field layout for one block
- is acceptable to `qa_entry_from_block_text(...)` as one block-shaped entry payload

Current ad hoc split top-level arrays (`issues`, `llm_issues`) should be replaced by one unified `rows` contract so deterministic and optional LLM issues share one shape.

## 5) Invariants

- Same deterministic normalization must be reused by validator and report generation.
- `de_1` acceptance must never depend on LLM alone; deterministic logic remains SSOT.
- Semantic paraphrase without lexical realization must not pass.
- Separable-verb support must prefer explicit stored forms over guessed morphology.
- Structural validator remains separate from semantic QA gate.
- Unresolved-block-tail placement must preserve valid `SSTART...EEND` block structure.
- Write file whenever at least one clean or unresolved-tail block exists.
- Return non-zero only when omitted entries remain.
- `mdproc.validation_core.iter_blocks(...)` is the shared parser for downstream block-parse decisions.
- unresolved-part routing must be decided by block-schema validity plus acceptance result, not by specific blocker family
- soft-review-only entries remain `clean` unless generation-time acceptance explicitly rejects them
- Same QA logic and report schema must run from both `run_full_pipeline.py` and `langgraph_app.py`.

## 6) Acceptance Criteria

- `voller Leidenschaft und mit ganzem Einsatz` is reported as failing sentence-shape validation.
- `Voller Leidenschaft und mit ganzem Einsatz.` is reported for review and does not silently pass.
- `Er arbeitet voller Leidenschaft und mit ganzem Einsatz.` passes.
- Target `eine warme Umgebung` reports `target_not_realized` for `ein freundlicher, fürsorglicher Ort`.
- Target `eine warme Umgebung` accepts `Kinder brauchen eine warme Umgebung.`
- Target `eine warme Umgebung` accepts `In so einer warmen Umgebung fühlen sich Pflanzen wohl.`
- Verb `zugreifen` accepts `Er greift sofort zu.` when stored form is `greift zu`.
- Verb `aufgeben` accepts `Er hat schon aufgegeben.`
- A sentence using plausible but unstored verb conjugation routes to `soft_review`, not silent pass.
- Invalid repaired entry with a structurally valid serialized block is placed in `## UNRESOLVED PART`, not omitted from file.
- Soft-review-only entry with valid block schema remains `clean` unless the generation acceptance contract explicitly rejects it.
- Failed-repair entry with last serialized valid block schema is placed in `## UNRESOLVED PART`, not omitted from file.
- Truly unserializable entry remains out of file and is reported as omitted.
- `run_full_pipeline.py` continues to NW3/NW4 when `Outputs/01_words.md` exists and contains at least one parseable block, even if NW1 exits non-zero because omitted entries remain.
- Parseable block count is computed with `mdproc.validation_core.iter_blocks(...)`, not a second ad hoc parser.
- Deterministic NW1 QA runs by default in both CLI pipeline entrypoints.
- QA report uses one unified `rows` schema.
- Clean blocks preserve input order, and unresolved-tail blocks preserve their relative input order.
- NW3/NW4-style block iteration still reads all written `SSTART...EEND` blocks with `## UNRESOLVED PART` present.

## 7) Non-Goals

- No post-pass auto-repair loop in this version.
- No second output file or JSON quarantine artifact in this version.
- No block-internal schema change for unresolved entries in this version.
- No full German parser or external POS tagger in first version.
- No semantic-embedding acceptance of paraphrases.
- No change to NW2–NW4 contracts in this spec.
- No unbounded auto-repair loop or second repair subsystem in `process_requirement1.py`.

## 8) Risks and Mitigations

- Risk: adjective-ending folding too narrow.
  - Mitigation: keep list intentionally small; ambiguous misses route to `soft_review`.
- Risk: phrase normalization may overmatch non-realized targets when tokens appear apart.
  - Mitigation: require one contiguous normalized span for phrase-like targets; reserve split matching for stored verb forms only.
- Risk: stored-form-only verb matching misses valid unstored conjugations.
  - Mitigation: mark those cases `soft_review`; do not guess unseen morphology.
- Risk: report schema drift between deterministic and LLM rows.
  - Mitigation: one SSOT row schema in `nw1_qa.py`.
- Risk: always-run QA adds noise to successful runs.
  - Mitigation: keep exit non-blocking and report machine-readable.

## 9) Validation Plan

- proof target: fragment without punctuation is reported as invalid
  - method: focused unit test
  - evidence: test case for `voller Leidenschaft und mit ganzem Einsatz`

- proof target: punctuated fragment still does not silently pass
  - method: focused unit test
  - evidence: test case for `Voller Leidenschaft und mit ganzem Einsatz.`

- proof target: realized phrase passes and paraphrase fails
  - method: focused unit test
  - evidence: tests for `eine warme Umgebung` examples

- proof target: explicit stored verb forms are accepted
  - method: focused unit test
  - evidence: tests for `greift zu` and `hat aufgegeben`

- proof target: unstored but plausible conjugation becomes `soft_review`
  - method: focused unit test + QA JSON inspection
  - evidence: issue severity `soft_review` in unified report row

- proof target: deterministic QA runs in both pipeline entrypoints
  - method: focused integration test or command-step inspection
  - evidence: step invocation in `run_full_pipeline.py` and `langgraph_app.py`

- proof target: generation-time repair rejects fragment and bare-lemma examples
  - method: focused unit test on `process_requirement1.py` repair acceptance path
  - evidence: tests covering `Ich möchte nicht, dass …`, `in der Kinderkrippe sein`, and `mitunter`

- proof target: unresolved-part entries remain parseable by downstream stages
  - method: focused unit test with mixed clean + unresolved-part output
  - evidence: `mdproc.validation_core.iter_blocks(...)` reads both sections and ignores marker lines

- proof target: failed-repair entry with last valid block is routed to unresolved part
  - method: focused unit test on `process_requirement1.py`
  - evidence: generated output contains `## UNRESOLVED PART` plus that block, while run still returns non-zero if omitted entries remain

- proof target: count reconciliation invariant holds
  - method: focused unit test on `process_requirement1.py`
  - evidence: `clean + unresolved_part + omitted == processed - skipped`

- proof target: pipeline continues past NW1 when parseable blocks exist
  - method: focused runner test on `run_full_pipeline.py`
  - evidence: NW3/NW4 steps are scheduled after NW1 non-zero result with usable `Outputs/01_words.md`

- proof target: omitted and blocker metadata stay in one SSOT report
  - method: focused QA/report test
  - evidence: unified `rows` payload carries `origin_reason_code`, `final_blocker_code`, and unresolved status without block-comment schema

- proof target: QA does not mutate NW1 output file
  - method: integration test with file hash before/after QA step
  - evidence: unchanged `Outputs/01_words.md` hash

## 10) Completion Criteria

- Detailed spec approved.
- Follow-on implementation plan created for bounded NW1 generation plus QA alignment changes only.
- Plan write scope remains minimal: `process_requirement1.py`, `nw1_qa.py`, `Prompt/nw1_enrich_instructions.md`, `nw1_qa_review.py`, pipeline entrypoints, and focused tests.
