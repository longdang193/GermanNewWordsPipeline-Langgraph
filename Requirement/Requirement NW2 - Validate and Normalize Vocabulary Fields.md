---
aliases: []
time: 2025-11-08-01-05-30
tags:
  - "#ANKI"
  - "#prompt"
status: []
TARGET DECK: []
---


## Objective

Process the German vocabulary file (`Outputs/01_words.md`) to normalize all fields and extract a clean word list.

## Prerequisites

- `mdproc` tool installed (see `Tools/README.md`)
- Input file: `Outputs/01_words.md` (vocabulary data)
- Validation tool: `Tools/scripts/validate_word_list.py`

## Current Project Structure (source of truth)

- Work from **repo root** (folder containing `Tools/`, `Inputs/`, `Outputs/`, `Requirement/`).
- NW2 is implemented by `mdproc` CLI:
  - `py -m mdproc process ...`
  - `py -m mdproc words ...`
- Optional full pipeline runner (NW1→NW4): `py Tools/scripts/run_full_pipeline.py`

## Processing Steps

### Step 0: Validate Word List Completeness (REQUIRED)

**Before normalizing**, verify that `Outputs/01_words.md` contains all words from Requirement NW1's Word List:

```powershell
cd "<repo_root>"
py Tools\scripts\validate_word_list.py
```

**What this does:**
- Extracts the Word List section from Requirement NW1
- Deduplicates the words in the list (case-insensitive)
- Counts unique words/phrases in the Word List
- Counts SSTART...EEND blocks in `Outputs/01_words.md`
- Compares the two counts to ensure completeness

**Expected outcome:**
- ✅ **VALIDATION PASSED**: Proceed to Step 1
- ❌ **VALIDATION FAILED**: Take corrective action before proceeding

**If validation fails:**
1. Review the missing count reported by the tool
2. Re-run Requirement NW1 to regenerate `Outputs/01_words.md` with all words
3. Re-validate before continuing to normalization steps

**Why this is critical:**
- Ensures no words are accidentally skipped during enrichment
- Catches incomplete processing early in the workflow
- Prevents propagating incomplete data to downstream steps

### Step 1: Normalize All Fields

Process the raw vocabulary file to apply all normalization rules:

```powershell
cd "<repo_root>"
py -m mdproc process Outputs/01_words.md --output Outputs/02_words_fixed.md
```

**What this does:**
- Renames `%WORD` → `WORD`
- Normalizes Gender field: `(Plural|Pluralwort)` → `(plural)`
- Normalizes Tags field: applies tag mapping, allowlist filtering, and sorting
- Removes trailing spaces and collapses multiple spaces
- Removes excessive blank lines

### Step 2: Extract Word List

Generate a deduplicated list of all words from the normalized file:

```powershell
py -m mdproc words Outputs/02_words_fixed.md --output Outputs/03_word_list.md
```

**What this does:**
- Extracts all `WORD` field values from `SSTART...EEND` blocks
- Deduplicates words (keeps first occurrence only)
- Outputs as Markdown bullet list format: `- word`

## Expected Outputs

### `Outputs/02_words_fixed.md`

- Normalized vocabulary blocks with corrected field formats
- Clean whitespace
- Standardized tags and gender fields

### `Outputs/03_word_list.md`

- Deduplicated word list in bullet format
- Words appear in source order (first occurrence)
- Example format:

	```markdown
	- Bauarbeiten
	- arbeiten
	- aufbauen
	```

## Validation

Before processing, verify:

- [ ] `Outputs/01_words.md` exists and contains vocabulary blocks
- [ ] **Word list completeness validated** (Step 0 passed)
- [ ] Block count matches Word List count from Requirement NW1

After processing, verify:

- [ ] No `%WORD` fields remain (all converted to `WORD`)
- [ ] All `(Plural)` or `(Pluralwort)` converted to `(plural)`
- [ ] Tags are lowercase, sorted, and only contain allowed values
- [ ] No trailing spaces on any line
- [ ] Word list has no duplicates

## Workflow Summary

```
Outputs/01_words.md         [Input from Requirement NW1]
	↓ (process)
Outputs/02_words_fixed.md   [Normalized fields]
	↓ (words)
Outputs/03_word_list.md     [Word list for Requirement NW3 Step 1]
```

## Notes

- **Validation is mandatory**: Do not skip Step 0. If validation fails, regenerate `Outputs/01_words.md` before proceeding
- **AI automation**: When executing Requirement 2, AI will automatically:
	1. Run the validation tool first
	2. If validation fails, trigger Requirement NW1 regeneration
	3. Re-validate after regeneration
	4. Only proceed to Steps 1-2 after successful validation
- The `process` command is idempotent (running it multiple times produces the same result)
- The `words` command preserves source order while removing duplicates
- Both commands respect UTF-8 encoding
