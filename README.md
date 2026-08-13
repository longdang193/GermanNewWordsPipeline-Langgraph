# GermanNewWordsPipeline

Pipeline take German word list → output Anki-ready vocab Markdown, with `see_also` cross-refs.

## What repo do

Input:
- `Inputs/Word List (DE).md`

Output (overwritten each run):
- `Outputs/01_words.md`
- `Outputs/02_words_fixed.md`
- `Outputs/03_word_list.md`
- `Outputs/04_see_also.md`
- `Outputs/05_see_also_fixed.md`
- `Outputs/06_words_final.md`
- `Outputs/06_words_final_fixed.md` (final deliverable)

Reports/logs (low-noise):
- `Outputs/reports/pipeline_state.json` (current resumable state)
- `Outputs/reports/run_latest.json`
- `Outputs/reports/runs.jsonl`
- `Outputs/logs/run_latest.log`

## Fast start (Windows)

### Option A: exe (recommended)

- Run: `dist/GermanNewWords/GermanNewWords.exe`
- Menu:
  - `Set word list path` → choose input file (copies into `Inputs/Word List (DE).md`)
  - `Run pipeline (fresh)`
  - `Resume last run`
  - `Auth NotebookLM` (if needed)

Prereq:
- Supported NotebookLM CLI: `uv tool install --force notebooklm-mcp-cli`
- `nlm` and `notebooklm-mcp` must resolve from the same `PATH` directory
- Python launcher `py` in `PATH` (exe uses it to run scripts)
- Verify: `dist/GermanNewWords/GermanNewWords.exe --root . doctor`

### Option B: Python runner

From repo root:
- Fresh pipeline: `py Tools/scripts/run_full_pipeline.py`
- Resume failed/interrupted pipeline: `py Tools/scripts/run_full_pipeline.py --resume`
- Installed CLI: `gnw run` or `gnw run --resume`

Fresh actions never resume automatically. `Resume last run` and `--resume` use `Outputs/reports/pipeline_state.json`; unchanged completed stages skip, while changed or incomplete stages rerun with dependents.

If resume rejects a corrupt state file, remove only `Outputs/reports/pipeline_state.json` and start fresh. Do not edit generated `Outputs/*.md` files or manually run downstream stages.

## NotebookLM

NW3 uses NotebookLM MCP to generate `see_also`:
- Tool: `Tools/scripts/generate_requirement3_notebooklm.py` (stdio MCP)
- Prompt SSOT: `Prompt/nw3_notebooklm_query.md` (template with `{word_list}`)
- Runtime knobs: `configs/runtime.toml`
- Auto auth uses the dedicated `~/.notebooklm-mcp/chrome-profile`; login in normal Chrome does not prove this profile is authenticated.
- If NW3 prints auth/session invalid or `Authentication expired`, run `dist/GermanNewWords/GermanNewWords.exe --root . auth`, then choose `Resume last run` or run `gnw run --resume`.
- If auto auth cannot detect login, run `gnw auth --file` and enter the cookie-file path, or run `nlm login --manual --file <path>` directly.
- If doctor reports mixed providers, inspect `where.exe nlm` and `where.exe notebooklm-mcp`.
- Remove legacy UV install with `uv tool uninstall notebooklm-mcp-server`, then reinstall supported CLI.

LLM structured-output compatibility is also configured in `configs/runtime.toml`:
- `[llm].prompted_structured_output_model_prefixes`
- Use this when an OpenAI-compatible backend supports JSON prompting but not tool-forced structured output for some model families.

NW1 LLM config ownership:
- `configs/runtime.toml` = runtime policy/defaults/flags
  - `[nw1].enable_llm_enrich`
  - `[llm].default_model`
  - `[llm].allow_default_openai_base_url`
  - `[llm].prompted_structured_output_model_prefixes`
- `.env` = machine-local values only
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL` (optional override; falls back to runtime default when missing)

Resolution order:
1. load `configs/runtime.toml`
2. load `.env` for missing environment variables
3. read stable `OPENAI_*` names
4. if `OPENAI_MODEL` missing, use `[llm].default_model`

## Prompt SSOT

Central prompts live in `Prompt/`:
- `Prompt/nw1_enrich_system.txt`
- `Prompt/nw1_enrich_instructions.md`
- `Prompt/nw1_qa_system.txt`
- `Prompt/nw1_qa_instructions.md`
- `Prompt/nw3_notebooklm_query.md`

Loader:
- `Tools/src/gnw_pipeline/prompts.py`

## Requirements docs

Spec intent live in `Requirement/`:
- `Requirement/Requirement NW1 - German new words prompt.md`
- `Requirement/Requirement NW2 - Validate and Normalize Vocabulary Fields.md`
- `Requirement/Requirement NW3 - Merge see_also Cross-References into Final Vocabulary Database.md`
- `Requirement/Requirement NW4 - Validate and Normalize see_also Anki References.md`

## Dev / tests

- Tests: `cd Tools && py -m pytest -q`
- Build exe: `pwsh -NoProfile -ExecutionPolicy Bypass -File Tools/scripts/build_windows_exe.ps1`

## Troubleshooting

- Proxy break NotebookLM MCP: clear `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`.
- Exe run from Explorer uses weird CWD; exe auto-detect repo root.
- Want see fail detail: open `Outputs/logs/run_latest.log`.
