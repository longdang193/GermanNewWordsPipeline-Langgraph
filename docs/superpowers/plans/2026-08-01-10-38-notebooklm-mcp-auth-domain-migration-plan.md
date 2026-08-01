---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: notebooklm-mcp-auth-domain-migration
parent_thread: current-thread
targets:
  - Tools/src/gnw_pipeline/notebooklm_runtime.py
  - Tools/src/gnw/__main__.py
  - Tools/src/gnw/ui.py
  - Tools/scripts/run_full_pipeline.py
  - Tools/scripts/generate_requirement3_notebooklm.py
  - Tools/tests/test_notebooklm_runtime.py
  - Tools/tests/test_gnw_cli.py
  - README.md
related_features:
  - notebooklm-auth
  - nw3-generation
  - runtime-doctor
related_stages:
  - NW3
---

# Note (canonical template gap)

Repository paths required by `skill-writing-plans` are missing locally: `docs/operating_system/templates/implementation-plan-template.md` and `docs/operating_system/tooling/code-intelligence-tools.md`. This plan follows current repository frontmatter and section shape.

# Goal

Prevent NW3 from entering the broken five-minute NotebookLM re-authentication wait by rejecting obsolete `notebooklm-mcp-server` before launch, standardizing on compatible `notebooklm-mcp-cli >= 0.9.4`, and giving every CLI/UI/pipeline entry point one shared authentication and installation-check contract.

# Scope

- In scope:
  - NotebookLM executable discovery and compatibility validation.
  - Shared NotebookLM authentication subprocess invocation.
  - `gnw doctor`, CLI auth, menu auth, direct NW3, and full-pipeline behavior.
  - Focused regression tests and root operator documentation.
- Preserved behavior:
  - NW3 continues using stdio MCP.
  - MCP tool names remain `refresh_auth`, `notebook_list`, and `notebook_query`.
  - Proxy variables remain cleared only for NotebookLM subprocesses.
  - Interactive auth and `--file` auth both remain supported.
  - Existing NW1, NW2, NW4, prompts, output formats, and runtime configuration remain unchanged.
- Out of scope:
  - Patching files under user `site-packages` or UV tool directories.
  - Bundling NotebookLM MCP inside `GermanNewWords.exe`.
  - Replacing stdio MCP with HTTP/SSE.
  - Changing NotebookLM notebook selection or query content.
  - Automatically uninstalling machine-global Python, UV, or npm packages.

# Diagnosis

- Current PATH resolves `notebooklm-mcp` and `notebooklm-mcp-auth` to UV-installed `notebooklm-mcp-server 0.1.15`.
- That implementation recognizes only `notebooklm.google.com` during Chrome page discovery and login detection.
- Current authenticated NotebookLM page resolves to `notebook.google.com`, so old auth CLI reports `NOT LOGGED IN` and waits 300 seconds despite a valid browser session.
- Compatible `notebooklm-mcp-cli 0.9.4` recognizes both hosts and preserves MCP commands and tool names used by NW3.
- Three command providers exist on affected machine, so checking command presence alone cannot prove PATH selects one compatible installation.

# Resolution Contract

1. `Tools/src/gnw_pipeline/notebooklm_runtime.py` owns NotebookLM executable compatibility, resolved command paths, and auth subprocess behavior.
2. Supported command set is `nlm`, `notebooklm-mcp`, and `notebooklm-mcp-auth` from one resolved executable directory.
3. Minimum accepted `nlm` version is `0.9.4`.
4. Version parsing accepts observed output `nlm version X.Y.Z` and rejects missing, malformed, or older versions.
5. Validation failures, version-command timeouts, and process launch errors return actionable messages and exit code `2`; they must not start Chrome or MCP server.
6. Auth subprocesses clear `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and lowercase equivalents in copied environment only.
7. `--file` is forwarded only when requested by `gnw auth --file`.
8. Direct NW3 validates installation before spawning `notebooklm-mcp`.
9. `gnw doctor` reports every missing, incompatible, or mixed-provider command and succeeds only when full NotebookLM command set is coherent.
10. Repository code never patches old-domain behavior inside third-party package internals.

# Key Deliverables

1. One small runtime helper containing compatibility check and auth runner.
2. One focused test file proving supported, missing, old, malformed, mixed-provider, proxy-clearing, and file-mode cases.
3. Thin CLI, UI, pipeline, and direct-NW3 consumers with no duplicate NotebookLM auth environment logic.
4. Updated installation and recovery instructions naming `notebooklm-mcp-cli` and `--file` fallback.

# Execution Approach

- Approach: `inline sequential`.
- One executor owns all tasks because `notebooklm_runtime.py` is shared dependency for every later edit.
- Required execution skills:
  - `skill-test-driven-development` for compatibility guard regression proof.
  - `skill-code-standards` for typed subprocess, path, and error handling.
  - `skill-verification-before-completion` for final focused and live checks.
- No subagents or parallel write lanes: files are small and dependency order is strict.
- Preserve unrelated existing changes in `Inputs/Word List (DE).md`, `Inputs/Word List (DE).bak`, and untracked `.serena/` state.

# Task 1 — Add NotebookLM runtime compatibility SSOT

**Files**
- Create `Tools/src/gnw_pipeline/notebooklm_runtime.py`.
- Create `Tools/tests/test_notebooklm_runtime.py`.

**Work**
- Define `NOTEBOOKLM_MCP_MIN_VERSION = (0, 9, 4)` as sole minimum-version owner.
- Add private `_inspect_notebooklm_install() -> tuple[dict[str, Path], list[str]]`:
  - resolve `nlm`, `notebooklm-mcp`, and `notebooklm-mcp-auth` with `shutil.which`;
  - report each missing command;
  - run resolved `nlm --version` with captured text and bounded timeout;
  - convert `subprocess.TimeoutExpired` and `OSError` into compatibility problems;
  - parse `nlm version X.Y.Z` using stdlib only;
  - reject malformed output, non-zero exit, and versions below minimum;
  - compare resolved parent directories and reject mixed command providers;
  - return resolved command paths with exact repair problems: `uv tool uninstall notebooklm-mcp-server` and `uv tool install --force notebooklm-mcp-cli`.
- Add public `notebooklm_install_problems() -> list[str]` as thin problem-only view used by doctor and direct NW3.
- Add `run_notebooklm_auth(*, cwd: Path, file_mode: bool = False) -> int`:
  - call `_inspect_notebooklm_install()` once and reuse returned auth executable path;
  - print each problem with `[FAIL]` and return `2` when incompatible;
  - copy environment and blank proxy variables only in that copy;
  - execute resolved `notebooklm-mcp-auth`, appending `--file` only for file mode;
  - convert auth launch `OSError` into `[FAIL]` output and exit code `2`;
  - return subprocess exit code unchanged.
- Keep helper synchronous; no classes, package managers, config files, or new dependency.

**Verification**
- Tests prove version `0.9.4` and newer pass.
- Tests prove missing `nlm`, old version, malformed output, and mixed executable directories fail.
- Test proves incompatible install does not invoke auth subprocess.
- Test proves proxy variables are blanked in child environment without mutating parent environment.
- Test proves `file_mode=True` appends exactly `--file`.
- Command: `py -m pytest Tools/tests/test_notebooklm_runtime.py -q`.

# Task 2 — Wire shared auth and doctor entry points

**Files**
- `Tools/src/gnw/__main__.py`
- `Tools/src/gnw/ui.py`
- `Tools/scripts/run_full_pipeline.py`
- `Tools/tests/test_gnw_cli.py`

**Work**
- In `gnw.__main__.cmd_auth`, replace local proxy/auth construction with `run_notebooklm_auth(cwd=root, file_mode=args.file_mode)`.
- In `gnw.__main__.cmd_doctor`, keep Python launcher checks and add `notebooklm_install_problems()` output; print `[OK]` only when no problems remain.
- Delete local `gnw.ui.run_notebooklm_auth`; import shared helper and call it directly from `run_ui` with `cwd=root`.
- Delete local `run_full_pipeline.run_notebooklm_auth`; import shared helper under same name and keep existing caller unchanged.
- Preserve menu text, CLI flags, and pipeline retry count.
- Update `test_gnw_cli.py` to mock shared helper boundary and cover doctor success plus incompatible NotebookLM installation.

**Verification**
- `gnw auth --file` reaches shared helper with `file_mode=True`.
- UI auth and pipeline auth reach shared helper with default `file_mode=False`.
- Doctor returns `2` for legacy/mixed installation and `0` for coherent compatible commands.
- Command: `py -m pytest Tools/tests/test_gnw_cli.py Tools/tests/test_run_full_pipeline.py -q`.

# Task 3 — Guard direct NW3 before MCP startup

**Files**
- `Tools/scripts/generate_requirement3_notebooklm.py`
- `Tools/tests/test_notebooklm_runtime.py`

**Work**
- Import `notebooklm_install_problems` after existing `Tools/src` path setup.
- At start of `main()`, before reading words or spawning MCP, print compatibility problems with `[error]` and return `2`.
- Leave `start_session()` protocol, initialization payload, `refresh_auth`, notebook lookup, query batching, resumable writes, and error classification unchanged.
- Do not add second compatibility check inside `start_session()`.

**Verification**
- Focused test proves incompatible installation exits before `subprocess.Popen`.
- Existing NotebookLM error classification tests remain unchanged and pass.
- Command: `py -m pytest Tools/tests/test_notebooklm_runtime.py Tools/tests/test_notebooklm_errors.py -q`.

# Task 4 — Update operator contract

**Files**
- `README.md`

**Work**
- Replace generic prerequisite wording with supported distribution `notebooklm-mcp-cli`.
- Document `uv tool uninstall notebooklm-mcp-server`, `uv tool install --force notebooklm-mcp-cli`, and `gnw doctor`.
- Explain auto auth uses dedicated Chrome profile; normal Chrome login does not prove MCP-profile validity.
- Document `notebooklm-mcp-auth --file` as manual fallback, not default recovery.
- Direct users to `where.exe nlm`, `where.exe notebooklm-mcp`, and `where.exe notebooklm-mcp-auth` when doctor reports mixed providers.
- Do not duplicate minimum version in README; `notebooklm_runtime.py` remains SSOT and doctor reports requirement.

**Verification**
- README commands match actual CLI command names.
- Source grep shows `notebooklm-mcp-server` only in migration/removal guidance and tests.
- Source grep shows one owner of `NOTEBOOKLM_MCP_MIN_VERSION`.

# Task 5 — Final verification and live smoke

**Files**
- No new code target; verification only.

**Work**
- Run focused tests and static checks.
- On affected machine, migrate PATH-selected UV tool outside repository changes.
- Verify command-provider coherence and current NotebookLM authentication.
- Run notebook-list smoke without full 42-word NW3 query.
- Inspect working tree and GitNexus affected flows before any commit.
- Stop for explicit operator approval before uninstalling or replacing machine-global UV tools.

**Verification**
- `py -m pytest Tools/tests/test_notebooklm_runtime.py Tools/tests/test_gnw_cli.py Tools/tests/test_run_full_pipeline.py Tools/tests/test_notebooklm_errors.py -q`
- `py -m ruff check --config Tools/pyproject.toml Tools/src/gnw_pipeline/notebooklm_runtime.py Tools/src/gnw/__main__.py Tools/src/gnw/ui.py Tools/scripts/run_full_pipeline.py Tools/scripts/generate_requirement3_notebooklm.py Tools/tests/test_notebooklm_runtime.py Tools/tests/test_gnw_cli.py`
- `py -m mypy --config-file Tools/pyproject.toml Tools/src/gnw_pipeline/notebooklm_runtime.py`
- Approval checkpoint before next two machine-global commands.
- `uv tool uninstall notebooklm-mcp-server`
- `uv tool install --force notebooklm-mcp-cli`
- `gnw --root . doctor`
- `dist/GermanNewWords/GermanNewWords.exe --root . doctor`
- `notebooklm-mcp-auth`
- `nlm notebook list --json`
- `git status --short`
- `gitnexus_detect_changes(scope="all")`

# Dependency Ordering

1. Task 1 first: every consumer depends on shared runtime helper and tests.
2. Task 2 after Task 1: entry points migrate to established helper contract.
3. Task 3 after Task 1: direct NW3 gains same compatibility result without duplication.
4. Task 4 after Tasks 1–3: documentation describes final command and error behavior.
5. Task 5 last: environment migration and live authentication occur only after code guards and tests exist.

# Rollback / Containment

- Revert consumer imports and restore prior local auth invocation if shared-helper wiring regresses; keep Task 1 tests and diagnosis for follow-up.
- Do not modify or delete `~/.notebooklm-mcp/auth.json` or dedicated Chrome profile during code execution.
- Do not uninstall npm or Python packages automatically; doctor reports conflicts and operator chooses machine cleanup.
- If `notebooklm-mcp-cli` changes MCP tool names in future, keep minimum-version guard, stop upgrade, and create separate compatibility change.
- If live authentication fails after coherent installation, use `notebooklm-mcp-auth --file`; do not reintroduce third-party source patching.

# Validation Rules

- Unsupported or ambiguous NotebookLM installation fails before Chrome or MCP startup.
- Compatible install preserves current NW3 stdio protocol and tool names.
- Parent process proxy variables remain unchanged.
- `--file` forwarding remains symmetric across direct CLI and shared auth runner.
- Minimum-version policy has one code owner.
- Documentation names install/migration commands but does not become version SSOT.
- No generated artifacts or user input files are modified by implementation or tests.

# Best Lazy Implementation

- One stdlib-only helper module.
- One focused test file.
- Direct shared-helper imports delete three duplicated auth launchers.
- Feature stays external; repository validates provider instead of vendoring or patching it.
- No packaging framework, adapter class, config schema, browser automation, or dependency addition.

# Verification

- Task-local pytest commands pass before final checks.
- Final focused pytest, Ruff, and mypy commands pass.
- `gnw doctor` identifies legacy or mixed PATH providers without launching Chrome.
- `nlm notebook list --json` succeeds after authentication.
- GitNexus change detection shows only NotebookLM auth/NW3/doctor execution paths expected by this plan.

# Completion Criteria

1. Legacy `notebooklm-mcp-server 0.1.15` cannot trigger five-minute auth wait through repo entry points.
2. Compatible `notebooklm-mcp-cli` installation passes doctor and direct NW3 preflight.
3. CLI, UI, pipeline, and direct NW3 use one compatibility/auth SSOT.
4. `notebook.google.com` authenticated sessions work through supported upstream package without repository monkey patches.
5. Focused tests and live notebook-list smoke provide reproducible proof.

# Precondition Note

This plan uses user-approved diagnosis and patch scope from current thread; no separate specification exists. If desired outcome changes from dependency migration/guarding to vendoring or patching NotebookLM MCP internals, draft and approve new specification before execution.
