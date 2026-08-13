---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: pipeline-stage-resume
targets:
  - Tools/scripts/run_full_pipeline.py
  - Tools/scripts/generate_requirement3_notebooklm.py
  - Tools/tests/test_run_full_pipeline.py
  - Tools/tests/test_notebooklm_runtime.py
  - Tools/scripts/README.md
  - README.md
related_features:
  - pipeline-orchestration
related_stages:
  - NW1
  - NW2
  - NW3
  - NW4
---

# Spec: Uniform pipeline-stage resume

## Note (canonical template gap)

Repo lacks canonical `docs/operating_system/...` templates referenced by agent skills. This spec follows required repository spec shape.

## Triage

Layer: change  
Feature type: MODIFY  
Summary: make failed pipeline runs resumable through one checkpoint manifest and one generic stage contract  
Affected stages: NW1, NW2, NW3, NW4  
Spec needed: yes  
Plan needed: yes

## 1) Goal

Provide one resumable execution model for every pipeline stage.

`py Tools/scripts/run_full_pipeline.py --resume` must safely continue current compatible run without rerunning completed, unchanged stages. New input or configuration must invalidate affected stage and every downstream stage.

Desired outcome:

- one canonical current-run state surface
- one stage contract and one skip rule for all stages
- safe recovery after command failure or process interruption
- no NW3-only orchestration exception
- no manual selection of downstream commands required

## 2) Current State

Observed facts:

- `run_full_pipeline.py` deletes `Outputs/01_words.md` before each run, so a full rerun starts NW1 again.
- NW3 incrementally writes `Outputs/04_see_also.md` and reloads valid blocks on later direct NW3 invocations.
- `run_latest.json` records only successful runs. A failed run leaves no authoritative resumable stage status.
- `runs.jsonl` is historical run reporting, not live execution control.

Root problem:

Pipeline progress exists partly in derived Markdown outputs and partly in process logs. Neither source uniformly records whether a stage completed against its current inputs.

Consequence:

After a recoverable failure, operators must infer a safe restart point and manually preserve or rerun outputs. Equivalent stage failures receive different recovery behavior.

## 3) Scope

In scope:

- resumable execution for every command stage in NW1 through NW4
- `--resume` and fresh-run behavior in full pipeline CLI
- explicit resume control through `gnw` CLI and packaged Windows UI
- one current-run checkpoint manifest
- uniform invalidation, skip, failure, interruption, and warning handling
- focused regression proof for state transitions

Out of scope:

- changing NW1/NW2/NW3/NW4 domain validation rules
- changing NotebookLM query semantics or retry limits
- preserving manual edits to derived `Outputs/*.md` files as source data
- parallel stage execution
- replacing `runs.jsonl` historical reporting

## 4) Design Decisions

### 4.1 Canonical state

`Outputs/reports/pipeline_state.json` is single source of truth for current resumable execution state.

It owns:

- current stage status
- input and output fingerprints
- stage-definition fingerprints
- command outcome, timestamps, and failure detail

Derived Markdown files remain stage outputs and verification evidence. `run_latest.json` remains success summary. `runs.jsonl` remains append-only history. Neither controls resume decisions.

### 4.2 One stage contract

Every logical stage uses same declared contract:

```text
id
dependencies
command
input_paths
output_paths
completion_policy
```

`completion_policy` is limited to existing outcome meanings:

- `success`: command exit status must be zero
- `usable_output`: command may exit non-zero only when existing stage-specific validator confirms usable output
- `warning`: command non-zero is recorded but does not block later stages

Stage-specific domain checks stay in existing validators. Orchestrator does not duplicate NW1, NW3, or NW4 validation rules.

Canonical logical stages:

1. `nw1_prepare`: generate, validate, and QA `Outputs/01_words.md`.
2. `nw2_prepare`: normalize NW1 output and extract `Outputs/02_words_fixed.md` plus `Outputs/03_word_list.md`.
3. `nw3_nw4_finalize`: generate `see_also`, preprocess and merge it, normalize and validate final output, run existing NW4 recovery loop when required, then run authenticity validation.

Commands, retries, interactive NotebookLM re-authentication, and recovery loops inside a logical stage are internal behavior. They do not create separate checkpoint states. This prevents recovery from mutating an upstream logical-stage output and creating a dependency cycle.

### 4.3 One completion rule

A stage is reusable only when all conditions hold:

1. stage status is `completed` or `completed_with_warnings`;
2. current fingerprint for stage definition matches saved fingerprint;
3. current fingerprints for declared stage inputs match saved fingerprints;
4. every declared stage output exists and matches saved fingerprint;
5. every dependency is reusable or completed in current invocation.

Otherwise stage is stale or incomplete and must execute.

No stage receives a custom resume path. NW3 incremental block loading remains internal to its normal command execution; it is not pipeline state.

### 4.4 State transitions

Allowed states:

```text
pending
running
completed
completed_with_warnings
failed
```

Transitions:

- fresh run creates every stage as `pending`;
- immediately before a command, runner persists `running`;
- successful completion persists `completed` with fingerprints;
- non-blocking outcome persists `completed_with_warnings` with fingerprints and warning detail;
- blocking outcome persists `failed` with exit code and captured error detail;
- a manifest found in `running` state after interruption is incomplete and reruns that stage on `--resume`.

State writes must be atomic. A damaged or unreadable manifest is not trusted; `--resume` stops with clear recovery instruction rather than guessing.

### 4.5 One active runner

Only one fresh or resume pipeline invocation may control current state at once.

Runner acquires a native exclusive lock before reading or writing checkpoint state and releases it on exit. A second invocation must exit without running stage commands and report that another pipeline run is active.

The lock is ephemeral coordination data, not a second source of execution truth. `pipeline_state.json` remains the only resumable state source.

### 4.6 Fresh and resume commands

Default command starts fresh run:

```powershell
py Tools/scripts/run_full_pipeline.py
```

Fresh run replaces current checkpoint state, then runs stages in declared order.

Resume command:

```powershell
py Tools/scripts/run_full_pipeline.py --resume
```

Resume loads `pipeline_state.json`, evaluates every logical stage through Section 4.3, skips reusable stages, and executes first stale or incomplete stage plus later stages under same rule.

If no manifest exists, `--resume` behaves as fresh run and creates state. A changed stage definition or stage input makes only that stage and its downstream dependents non-reusable. No second live checkpoint source is created.

### 4.7 Distribution interface symmetry

Resume is explicit. Distribution must not automatically resume a prior run when user starts the executable or selects fresh pipeline execution.

Supported public commands:

```powershell
gnw run
gnw run --resume
```

`gnw run` starts fresh. `gnw run --resume` forwards resume intent to the same pipeline runner. Neither CLI wrapper nor packaged executable owns checkpoint, invalidation, stage-selection, or recovery logic.

`Tools/scripts/run_full_pipeline.py` is authoritative runner for both `gnw run` modes and both Windows UI actions. `gnw` must not select the optional LangGraph path for these public commands because it has separate step definitions and no checkpoint contract.

Windows UI must expose two distinct user actions:

- `Run pipeline (fresh)` forwards fresh intent.
- `Resume last run` forwards resume intent.

`Resume last run` may be selected even when no checkpoint exists; runner applies Section 4.6 and starts fresh. UI must not parse checkpoint state to decide eligibility. This keeps all interfaces symmetric and leaves one resume decision owner.

### 4.8 Invalidation symmetry

Every stage fingerprint includes:

- command arguments and completion policy;
- repo-owned scripts and modules that directly determine stage output;
- relevant prompt and runtime configuration files;
- fingerprints of declared dependency outputs.

Changing an input invalidates that stage and all dependent stages. Changing unrelated earlier-stage outputs does not invalidate independent stages because pipeline is sequential and all current stages are dependency-linked only when data actually flows between them.

Manual mutation of a declared derived output changes its output fingerprint. Resume treats producing stage as stale and regenerates it. This preserves source-of-truth boundaries: user edits belong in canonical inputs, prompts, configuration, or scripts, not generated outputs.

### 4.9 Existing warning semantics

Current continuation behavior remains explicit and symmetric:

- NW1 generation or validation with parseable usable blocks: `completed_with_warnings`.
- NW1 QA report findings: `completed_with_warnings`.
- NW3/NW4 authenticity warnings: `completed_with_warnings`.
- Any stage without its required usable output: `failed`.

Warnings must retain existing log text and report context. Resume may skip warning-completed stages only when Section 4.3 holds.

## 5) Manifest Contract

Minimum JSON shape:

```json
{
  "schema_version": 1,
  "stages": [
    {
      "id": "nw3_nw4_finalize",
      "dependencies": ["nw2_prepare"],
      "status": "completed",
      "definition_fingerprint": "sha256",
      "input_fingerprint": "sha256",
      "output_fingerprints": {
        "Outputs/04_see_also.md": "sha256",
        "Outputs/05_see_also_fixed.md": "sha256",
        "Outputs/06_words_final.md": "sha256",
        "Outputs/06_words_final_fixed.md": "sha256"
      },
      "started_at_utc": "ISO-8601",
      "finished_at_utc": "ISO-8601",
      "exit_code": 0,
      "detail": null
    }
  ]
}
```

Requirements:

- `schema_version` permits explicit future migration.
- Stage IDs are stable, unique, ordered through dependencies, and owned by stage registry.
- Fingerprints use SHA-256 of exact bytes for declared files plus stable stage configuration values.
- `definition_fingerprint` covers command arguments, completion policy, and declared repo-owned implementation files.
- `detail` is `null` for clean success; otherwise concise captured warning or error context.
- Credential values, NotebookLM cookies, prompts containing secrets, and environment variables must never enter manifest.

## 6) Compatibility and Failure Behavior

- Existing no-argument full-run command remains supported and retains fresh-run behavior.
- Existing `gnw run` and Windows UI fresh-run action retain fresh-run behavior.
- `gnw run --resume` and Windows UI resume action invoke same pipeline runner with resume intent.
- `gnw` public pipeline commands invoke `Tools/scripts/run_full_pipeline.py` regardless of optional LangGraph installation.
- Existing output filenames remain unchanged.
- Existing direct helper scripts remain runnable, but documented supported recovery path becomes full-run `--resume`.
- First run after feature release creates state from scratch; it must not infer completion from stale outputs without recorded checkpoint evidence.
- Missing declared output, output fingerprint mismatch, changed input, failed stage, interrupted stage, and absent state each follow same rule: rerun first non-reusable stage.
- Unreadable state is fail-safe. Operator removes only `Outputs/reports/pipeline_state.json` to intentionally begin fresh state; runner must never delete other outputs as automatic repair.
- A second active invocation exits before executing any stage command.

## 7) Acceptance Criteria

### Acceptance Criterion: Resume failed NW3

- setup: NW1/NW2 completed; `nw3_nw4_finalize` writes partial `Outputs/04_see_also.md` then exits non-zero.
- action: run `py Tools/scripts/run_full_pipeline.py --resume`.
- expected result: NW1/NW2 are skipped; `nw3_nw4_finalize` reruns; its normal NW3 block cache reuses valid existing blocks; manifest ends with each logical-stage outcome.
- failure condition: runner deletes or regenerates unchanged NW1/NW2 outputs.
- proof method: focused runner test with recorded commands and manifest inspection.
- expected evidence: finalization stage invoked; NW1/NW2 stages absent.

### Acceptance Criterion: Invalidate downstream stages

- setup: full pipeline state completed.
- action: change a declared `nw3_nw4_finalize` input, then run `--resume`.
- expected result: NW1/NW2 remain skipped; `nw3_nw4_finalize` reruns.
- failure condition: unchanged upstream stages rerun or affected downstream stage skips.
- proof method: focused runner test.
- expected evidence: stage invocation list and updated fingerprints.

### Acceptance Criterion: Recover interruption

- setup: manifest records a stage as `running`.
- action: run `--resume`.
- expected result: runner re-executes that stage; no later stage runs before it completes.
- failure condition: runner treats `running` as successful.
- proof method: focused runner test.
- expected evidence: updated terminal state and command order.

### Acceptance Criterion: Preserve warnings

- setup: NW1 validator returns non-zero while parseable usable blocks exist.
- action: run fresh pipeline, then `--resume` without changes.
- expected result: NW1 warning outcome is recorded once; unchanged stage is skipped on resume.
- failure condition: warning outcome becomes failed or reruns needlessly.
- proof method: focused runner test.
- expected evidence: `completed_with_warnings` state and skipped command.

### Acceptance Criterion: Reject corrupt state

- setup: `pipeline_state.json` contains invalid JSON.
- action: run `--resume`.
- expected result: command stops before pipeline command execution and reports state-file recovery action.
- failure condition: runner guesses stage status or mutates outputs.
- proof method: focused runner test.
- expected evidence: non-zero exit and no stage command calls.

### Acceptance Criterion: Reject concurrent run

- setup: one pipeline invocation holds active runner lock.
- action: start second fresh or `--resume` invocation.
- expected result: second invocation exits before stage commands run and identifies active-run condition.
- failure condition: both invocations run or mutate `pipeline_state.json`.
- proof method: focused runner test with held lock.
- expected evidence: non-zero exit and no second-run command calls.

### Acceptance Criterion: Preserve explicit distribution intent

- setup: packaged CLI and Windows UI are available.
- action: invoke `gnw run`, invoke `gnw run --resume`, choose `Run pipeline (fresh)`, and choose `Resume last run`.
- expected result: fresh actions forward fresh intent; resume actions forward resume intent; none infer stage state or auto-resume.
- failure condition: opening executable, choosing fresh action, or `gnw run` resumes prior state.
- proof method: focused CLI and UI dispatch tests with mocked pipeline runner.
- expected evidence: recorded calls distinguish only `resume=False` and `resume=True`.

## 8) Non-Goals

- No per-stage state files.
- No database, job scheduler, lock service, queue, or parallel execution.
- No special checkpoint mechanism for NotebookLM, NW1, or NW4.
- No dist-specific resume function, state parser, or checkpoint policy.
- No automatic repair of invalid source content.
- No recovery based on parsing logs.
- No checkpoint history guarantee beyond existing successful-run summaries.

## 9) Risks and Mitigations

- Risk: output hashes add I/O cost. Mitigation: Markdown outputs are small; hash once at stage boundary.
- Risk: outputs changed outside pipeline. Mitigation: fingerprint mismatch forces deterministic regeneration.
- Risk: state schema evolves. Mitigation: version manifest and reject unsupported versions clearly.
- Risk: stale output is manually needed. Mitigation: derived outputs are not edit targets; canonical inputs remain untouched by resume logic.

## 10) Completion Criteria

- Specification approved.
- Implementation creates one state manifest and one stage registry.
- Fresh and resume commands meet all acceptance criteria.
- Existing pipeline output contracts remain intact.
