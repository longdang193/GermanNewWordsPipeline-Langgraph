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
- `Outputs/reports/run_latest.json`
- `Outputs/reports/runs.jsonl`
- `Outputs/logs/run_latest.log`

## Fast start (Windows)

### Option A: exe (recommended)

- Run: `dist/GermanNewWords/GermanNewWords.exe`
- Menu:
  - `Set word list path` → choose input file (copies into `Inputs/Word List (DE).md`)
  - `Run pipeline`
  - `Auth NotebookLM` (if needed)

Prereq:
- `notebooklm-mcp` and `notebooklm-mcp-auth` in `PATH`
- Python launcher `py` in `PATH` (exe uses it to run scripts)

### Option B: Python runner

From repo root:
- Full pipeline: `py Tools/scripts/run_full_pipeline.py`

## NotebookLM

NW3 uses NotebookLM MCP to generate `see_also`:
- Tool: `Tools/scripts/generate_requirement3_notebooklm.py` (stdio MCP)
- Prompt SSOT: `Prompt/nw3_notebooklm_query.md` (template with `{word_list}`)
- Runtime knobs: `configs/runtime.toml`
- If NW3 prints auth/session invalid or `Authentication expired`, rerun `dist/GermanNewWords/GermanNewWords.exe --root . auth --clear-proxy`, then rerun pipeline.

LLM structured-output compatibility is also configured in `configs/runtime.toml`:
- `[llm].prompted_structured_output_model_prefixes`
- Use this when an OpenAI-compatible backend supports JSON prompting but not tool-forced structured output for some model families.

If auth expired:
- Run `notebooklm-mcp-auth`

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
