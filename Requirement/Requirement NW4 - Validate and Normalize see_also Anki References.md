---
aliases: []
time: 2025-10-15-14-15
updated: 2026-04-07T00:00:00.000Z
tags:
  - "#language-german"
  - "#ANKI"
  - "#prompt"
status: updated-with-tools
---


## Task Description

Normalize and validate all `see_also` field entries, and validate noun `noun_forms` consistency, using the automated processing tools.

### Prerequisites

* **mdproc tool installed** (see `Tools/README.md`)
* **Completed Requirements NW1-NW3** (must have `Outputs/06_words_final.md`)

### Input

* **Folder:** `Outputs`
* **File:** `Outputs/06_words_final.md` (complete vocabulary database from Requirement NW3)

### Output

* **Folder:** `Outputs`
* **File:** `Outputs/06_words_final_fixed.md` (normalized and validated final database)

## Automated Processing Steps

### Step 1: Normalize see_also References

Process the vocabulary file to normalize all `see_also` entries:

```powershell
cd "<repo_root>"
python Tools\scripts\process_requirement4.py
```

**What this does:**
- Ensures proper bracket completion for all references
- Cleans NID formatting (removes `<>` characters)
- Preserves gender markers with correct spacing
- Normalizes whitespace and formatting
- Validates syntax compliance
- Preserves noun-related fields so downstream validation can verify `noun_forms`

### Step 2: Validate Results

Verify the normalization with validation tools:

```powershell
# Comprehensive validation (authoritative)
python Tools\scripts\validate_requirement4.py

# Optional quick validation and statistics
python Tools\scripts\final_validate.py
```

If NW4 reports missing required non-phrase `see_also` fields or non-canonical `see_also` syntax, run:

```powershell
python Tools\scripts\recover_missing_seealso.py
```

Then re-run Step 1 and Step 2 validators.

`recover_missing_seealso.py` automatically:
- detects words with missing required non-phrase `see_also`,
- detects words that still contain non-canonical `see_also` lines,
- queries NotebookLM MCP only for affected words,
- upserts `Outputs/04_see_also.md` by `word:` (replace existing blocks for repaired words; append new words),
- rebuilds `Outputs/05_see_also_fixed.md`, `Outputs/06_words_final.md`, and `Outputs/06_words_final_fixed.md`.

## Objective

Ensure that **every entry** in the `see_also:` field strictly adheres to the canonical syntax:

```
([gender]) [related_word|nid<anki_note_id>] = short English meaning
```

For nouns, `gender` is mandatory and must be one of `der`, `die`, `das`.
For verbs/adjectives/adverbs/phrases, gender is omitted.

Also ensure German-facing content is orthographically correct and does not use ASCII transliteration placeholders (`ae`, `oe`, `ue`) where umlauts are expected.

Also enforce `word:` field hygiene:
- `word:` must not include parenthetical meaning/gloss text.
  - Invalid: `word: bestehen (pass, overcome)`
  - Valid: `word: bestehen`
- For noun blocks, `word:` must not start with `der` / `die` / `das`.
  - Invalid: `word: das Aufregendste`
  - Valid: `word: Aufregendste`

## Correct Syntax Examples

```
see_also:
[wirklich|nid1718783286443] = ...
der [Tisch|nid1718783200012] = ...
die [Schule|nid1718783007890] = ...
das [Buch|nid1718783011234] = ...
[es fällt mir schwer|nid1759139706760] = ...
```

## Normalization Logic

### Bracket Completion

* Ensure each reference is fully enclosed in square brackets `[ ... ]`.
* If a left or right bracket is missing, insert it automatically.

**Examples:**

```
wirklich|nid1718783286443]  →  [wirklich|nid1718783286443]
wirklich|nid1718783286443   →  [wirklich|nid1718783286443]
[wirklich|nid1718783286443  →  [wirklich|nid1718783286443]
```

### NID Cleanup

* Remove extraneous characters (`<`, `>`) surrounding the numeric ID.
* Normalize all variations of `nid<123>` or `nid<123>` to `nid123`.

**Examples:**

```
[wirklich|nid<1718783286443>]  →  [wirklich|nid1718783286443]
[wirklich|nid1718783286443>]   →  [wirklich|nid1718783286443]
```

### Gender Preservation

* Retain any gender marker preceding the bracket.
* Gender must:
	* Be enclosed in parentheses.
	* Be followed by **exactly one space** before the bracket.

**Valid forms:**

```
der [ ... ]
die [ ... ]
das [ ... ]
(pl.) [ ... ]
```

**Mandatory noun form:**

```
die [Auskunft|nid...]
```

**Invalid noun form:**

```
[Auskunft|nid...]
```

### Whitespace Normalization

* No spaces are allowed **inside** brackets.
* Exactly one space is required between gender and the bracket.
* Remove trailing or redundant spaces from all lines.

### Multiple References Handling

* When multiple `see_also` references exist, each must appear on a new line.
* Every entry must be syntactically complete and self-contained.

## Final Example (Multiple References)

```
see_also:
der [Tisch|nid1718783200012] = table
die [Schule|nid1718783007890] = school
[wirklich|nid1718783286443] = really
[es fällt mir schwer|nid1759139706760] = ...
```

## Tool Roles

Use one authoritative validator and keep quick validation optional:

- `Tools/scripts/process_requirement4.py`
  - Normalizes `see_also` formatting and writes `Outputs/06_words_final_fixed.md`.
- `Tools/scripts/validate_requirement4.py` (authoritative)
  - Role: Single authoritative NW4 pass/fail validator used by automation.
  - It enforces line-level syntax, structural constraints, and field-level quality rules.
- `Tools/scripts/final_validate.py` (optional)
  - Role: Fast human-readable diagnostics (counts, samples, basic formatting checks).
  - Use this for quick inspection, not as the final pass/fail gate.

## Expected Outputs

### Outputs/06_words_final_fixed.md

- Complete vocabulary database with normalized `see_also` references
- All entries conform to canonical syntax
- Ready for Anki import or further processing
- UTF-8 encoding with proper line endings

### Console Output

- Processing status and completion confirmation
- Validation results and statistics
- Error reports (if any issues found)
- Sample entries for verification

## Output Requirements

* The output file must be:
	* **Syntactically valid:** all `see_also` entries conform to the defined structure.
	* **Machine-parseable:** safe for automated import into Obsidian or Anki.
	* **Human-readable:** cleanly formatted, with consistent spacing and alignment.

## Validation Criteria

After processing, verify:

- [ ] All `see_also` entries follow canonical syntax
- [ ] All non-phrase blocks contain a non-empty `see_also` field
- [ ] No malformed NID entries (no `<>` characters)
- [ ] All entries have proper bracket completion
- [ ] Gender markers have correct spacing
- [ ] Noun-like `see_also` terms always include `der`/`die`/`das`
- [ ] `word:` does not include parenthetical meaning/gloss text
- [ ] Noun `word:` does not start with `der`/`die`/`das`
- [ ] Every noun block has a `noun_forms` field
- [ ] Every noun `noun_forms` value uses `genitive, plural` format
- [ ] Every noun `noun_forms` value is consistent with `noun_genetiv` and `noun_plural`
- [ ] No ASCII transliterations (`ae`, `oe`, `ue`) remain in German-facing fields
- [ ] No ASCII transliterations (`ae`, `oe`, `ue`) remain in `see_also` related-word terms
- [ ] File encoding is UTF-8
- [ ] All original vocabulary data is preserved
- [ ] Total entry count matches input file

## Workflow Summary

```
Outputs/02_words_fixed.md   [From Requirement NW2]
  ↓ (words)
Outputs/03_word_list.md     [Used by Requirement NW3 Step 1]
  ↓ (NotebookLM MCP + SSOT prompt `Prompt/nw3_notebooklm_query.md`)
Outputs/04_see_also.md      [Generated cross-references]
  ↓ (preprocess)
Outputs/05_see_also_fixed.md [Preprocessed cross-references]
  ↓ (merge-see-also)
Outputs/06_words_final.md   [Input from Requirement NW3]
    ↓ (process_requirement4.py)
Outputs/06_words_final_fixed.md [Normalized see_also references]
  ↓ (validate_requirement4.py)
Validation Report           [Confirmation and statistics]
```

## Notes

- The processing is **non-destructive** (preserves all original vocabulary data)
- The tools are **idempotent** (running multiple times produces same result)
- All scripts include error handling and detailed logging
- The output is **Anki-ready** for immediate import
- Processing typically completes in under 1 second for standard vocabulary files

## Current Project Structure (source of truth)

- Full pipeline runner (NW1→NW4): `py Tools/scripts/run_full_pipeline.py`
- Final deliverable: `Outputs/06_words_final_fixed.md`
- Reports/logs (low-noise):
  - `Outputs/reports/run_latest.json`
  - `Outputs/logs/run_latest.log`

## Troubleshooting

### Common Issues

**Script not found**: Ensure you're in the correct directory and the Tools directory structure is intact.

**Import errors**: Verify mdproc is installed with `pip install -e Tools/`

**File not found**: Ensure `Outputs/06_words_final.md` exists (complete Requirements 1-3 first)

**Permission errors**: Ensure write permissions to the output directory

### Getting Help

- Check `Tools/README.md` for detailed tool documentation
- Review `Tools/scripts/README.md` for script-specific information
- Use the validation tools to identify specific syntax issues
- Examine the console output for detailed error messages
