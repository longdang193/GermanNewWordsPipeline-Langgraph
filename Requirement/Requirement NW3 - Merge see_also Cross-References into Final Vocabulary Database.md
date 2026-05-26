---
aliases: []
time: 2025-11-08-01-05-41
tags:
  - "#ANKI"
  - "#prompt"
status: []
TARGET DECK: []
---


## Objective

Merge cross-reference data (`see_also` fields) from a separate file into the main normalized vocabulary file to create the final, complete vocabulary database.

## Prerequisites

- `mdproc` tool installed (see `Tools/README.md`)
- Completed Requirement NW2 (must have `Outputs/02_words_fixed.md`)
- `NotebookLM MCP` configured and authenticated
- Notebook selected in NotebookLM MCP (project default): `Comprehensive German Language Learning and Vocabulary Guide`
- Proxy variables cleared for NotebookLM access when needed (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` must not point to dead local proxy such as `127.0.0.1:9`)
- Input files:
	- `Outputs/02_words_fixed.md` - Normalized vocabulary from Requirement NW2
	- `Prompt/nw3_notebooklm_query.md` - SSOT query prompt template for generating `see_also` references (uses `{word_list}`)
	- `configs/runtime.toml` - runtime knobs (batching, min/max see_also entries)

## Processing Steps

### Step 1: Generate `Outputs/03_word_list.md`, then `Outputs/04_see_also.md`

First generate `Outputs/03_word_list.md` from Requirement NW2 output, then generate `Outputs/04_see_also.md` via NotebookLM MCP.
For this project, the NotebookLM MCP query must use notebook `Comprehensive German Language Learning and Vocabulary Guide`.
The process must work for any current content of `Outputs/03_word_list.md` (no fixed word-count assumptions).

Do this before Step 2:

1. Generate the word list file:

```powershell
py -m mdproc words Outputs/02_words_fixed.md --output Outputs/03_word_list.md
```

2. Preferred automated generation (recommended):

```powershell
cd "<repo_root>"
py Tools/scripts/generate_requirement3_notebooklm.py
```

This uses:
- notebook title: `Comprehensive German Language Learning and Vocabulary Guide`
- prompt template: `Prompt/nw3_notebooklm_query.md`
- runtime rules: `configs/runtime.toml`

Key invariant:
- Each `see_also:` block must contain **3 to 5 entries** (enforced; blocks outside range are rejected and re-queried).

3. Manual generation (fallback):
   - Use prompt template `Prompt/nw3_notebooklm_query.md` and fill `{word_list}` with the contents of `Outputs/03_word_list.md`.
   - In NotebookLM MCP, select notebook `Comprehensive German Language Learning and Vocabulary Guide`.
   - Before running, clear dead proxy env vars for the MCP process and query shell:

```powershell
$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:ALL_PROXY=''
$env:http_proxy=''; $env:https_proxy=''; $env:all_proxy=''
```

4. Write the generated `see_also` blocks to `Outputs/04_see_also.md` in `SSTART...EEND` format.
5. Ensure each block contains `word:` (or `%word:`) and a `see_also:` section (one reference per line).
6. If NW4 later reports missing required `see_also` entries or non-canonical `see_also` syntax, run a targeted re-query for only affected words and upsert blocks in `Outputs/04_see_also.md` by `word:` (replace existing blocks for repaired words, append only new words).
7. Preferred automated recovery command:

```powershell
python Tools/scripts/recover_missing_seealso.py
```

Step 1 is complete only when:

- `Outputs/03_word_list.md` exists and is UTF-8 encoded.
- `Outputs/04_see_also.md` exists and is UTF-8 encoded.
- The file contains only valid vocabulary blocks (no free-text commentary).
- Every generated block is intended to match a word from `Outputs/02_words_fixed.md`.
- Coverage is evaluated against the current `Outputs/03_word_list.md`, not against any hardcoded list size.
- Any missing or non-canonical gaps found by NW4 are recovered via targeted re-query before proceeding to final validation.
- Recovery can be executed manually or with `Tools/scripts/recover_missing_seealso.py`.

### Step 2: Preprocess the `see_also` File

Clean and deduplicate the `see_also` reference file:

```powershell
cd "<repo_root>"
py -m mdproc preprocess Outputs/04_see_also.md --output Outputs/05_see_also_fixed.md
```

**What this does:**
- Deduplicates blocks by `WORD` (keeps first occurrence, drops duplicates)
- Renames `%WORD` → `WORD`
- Removes trailing spaces
- Collapses multiple spaces
- Normalizes blank lines

Step 2 starts only when:

- `Outputs/03_word_list.md` and `Outputs/04_see_also.md` are generated from Step 1.

Step 2 is complete only when:

- `Outputs/05_see_also_fixed.md` exists and is UTF-8 encoded.
- Duplicate `WORD` blocks have been removed (first occurrence retained).
- Block structure is still valid for downstream merge processing.

### Step 3: Merge `see_also` into Final File

Inject the cross-references into the main vocabulary file:

```powershell
py -m mdproc merge-see-also Outputs/05_see_also_fixed.md Outputs/02_words_fixed.md --output Outputs/06_words_final.md
```

**What this does:**
- For each word in `Outputs/05_see_also_fixed.md` that has a `see_also` field:
	- Finds matching `WORD` block in `Outputs/02_words_fixed.md`
	- Inserts/updates the `see_also` section in the correct position
	- **Placement**: Above `Tags` field (or above `EEND` if no Tags)
	- Deduplicates `see_also` entries within each block (preserves first-seen order)

Step 3 starts only when:

- `Outputs/05_see_also_fixed.md` (from Step 2) and `Outputs/02_words_fixed.md` are both available.

Step 3 is complete only when:

- `Outputs/06_words_final.md` exists and is UTF-8 encoded.
- `see_also` fields are merged only into matching `WORD` blocks.
- No non-`see_also` fields from `Outputs/02_words_fixed.md` are modified.

## Expected Output

### `Outputs/05_see_also_fixed.md` (Intermediate)

- Cleaned `see_also` reference data
- No duplicate `WORD` blocks
- Normalized whitespace

### `Outputs/06_words_final.md` (Final Output)

- Complete vocabulary database
- All normalized fields from `Outputs/02_words_fixed.md`
- Cross-references merged from `Outputs/05_see_also_fixed.md`
- `see_also` fields positioned correctly (above `Tags` or above `EEND`)

**Example block structure:**

```markdown
SSTART
%VOCAB (German) ver 3
word: Bauarbeiten
meaning: die Bauarbeiten = construction work
de_1: Die Bauarbeiten dauern noch zwei Wochen.
en_1: The construction work will last another two weeks.
word_inf: die Bauarbeiten
noun_gender: die (plural)
noun_genetiv: -
noun_plural: Bauarbeiten
noun_forms: -
see_also:
die [Arbeit|nid1718783284444] = work
[arbeiten|nid1718783284443] = to work
Tags: compound noun
EEND
```

## Validation

After processing, verify:

- [ ] All words from `Outputs/02_words_fixed.md` are present in `Outputs/06_words_final.md`
- [ ] `see_also` fields are correctly positioned (above `Tags` or above `EEND`)
- [ ] No duplicate entries within individual `see_also` sections
- [ ] All field normalizations from Requirement NW2 are preserved
- [ ] File encoding is UTF-8

## Workflow Summary

```
Outputs/01_words.md         [Raw vocabulary data]
    ↓ (process)
Outputs/02_words_fixed.md   [Normalized fields]
	↓ (words)
Outputs/03_word_list.md     [Word list for NotebookLM MCP query]
	↓ (NotebookLM MCP on notebook "Comprehensive German Language Learning and Vocabulary Guide" + SSOT prompt `Prompt/nw3_notebooklm_query.md`)
Outputs/04_see_also.md      [Generated cross-references]
	↓ (preprocess)
Outputs/05_see_also_fixed.md [Preprocessed cross-references]
	↓ (merge-see-also)
    ↓
Outputs/06_words_final.md   [Final complete vocabulary database]
```

## Notes

- The merge operation is non-destructive (only adds/updates `see_also` fields)
- If a word appears in `Outputs/04_see_also.md` but not in `Outputs/02_words_fixed.md`, it won't be added
- The merge preserves all other fields from `Outputs/02_words_fixed.md` unchanged
- `see_also` entries are deduplicated per block, maintaining first-seen order
