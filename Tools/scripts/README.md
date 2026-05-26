# Scripts Directory

This directory contains specialized scripts for processing German vocabulary requirements.

## Scripts Overview

### Requirement Processing

#### `process_requirement1.py`
**Purpose**: Generate enriched German vocabulary entries from word list  
**Usage**: `python scripts/process_requirement1.py`  
**Input**: Word list from Requirement 1 file  
**Output**: `Outputs/01_words.md` with ver 3 formatted entries

**What it does**:
- Extracts words from Requirement 1's Word List section
- Detects part of speech (noun, verb, adjective, phrase)
- Generates entries using ver 3 templates with lowercase field names
- Enriches minimal phrases for clarity (e.g., "dabei haben" → "dabei etwas haben")
- Deduplicates entries within the current run (case-insensitive)
- Rebuilds `Outputs/01_words.md` from scratch with metadata header
- Rejects formulaic dummy examples and generic sentence shells

**Template Version**: ver 3 (lowercase fields: `word:`, `meaning:`, `de_1:`, `en_1:`, etc.)

#### `validate_word_list.py`
**Purpose**: Validate that `Outputs/01_words.md` contains all words from Requirement 1  
**Usage**: `python scripts/validate_word_list.py`  
**Input**: Requirement 1 file and `Outputs/01_words.md`

**What it does**:
- Extracts and deduplicates Word List from Requirement 1
- Counts unique words in the requirement
- Counts strict `SSTART...EEND` blocks in `Outputs/01_words.md`
- Rejects legacy block markers `START...END`
- Rejects unreplaced template placeholders (for example: `[simple German meaning(s)]`, `(Example sentence ...)`)
- Detects path drift when legacy root-level files are used
- Compares counts to ensure completeness
- Reports missing entries if validation fails

**When to use**: Before proceeding to Requirement 2 processing

#### `process_requirement4.py`
**Purpose**: Normalize and validate `see_also` Anki references  
**Usage**: `python scripts/process_requirement4.py`  
**Input**: `Outputs/06_words_final.md`  
**Output**: `Outputs/06_words_final_fixed.md`  

**What it does**:
- Ensures all `see_also` entries follow canonical syntax: `([gender]) [word|nid<digits>] = meaning`
- Completes missing brackets automatically
- Cleans NID formatting (removes `<>` characters)  
- Preserves gender markers with proper spacing
- Normalizes whitespace and formatting
- Validates strict block markers (`SSTART...EEND`) and rejects `START...END`

### Validation Tools

#### `final_validate.py`
**Purpose**: Optional quick validation and statistics for processed files  
**Usage**: `python scripts/final_validate.py`  
**Target**: `Outputs/06_words_final_fixed.md`

**Role:** Fast human-readable diagnostics (counts, samples, basic formatting checks).
Use this for quick inspection, not as the final pass/fail gate.

#### `validate_requirement4.py`  
**Purpose**: Authoritative comprehensive validation with detailed error reporting  
**Usage**: `python scripts/validate_requirement4.py`  
**Target**: `Outputs/06_words_final_fixed.md`

**Role:** Single authoritative NW4 pass/fail validator used by automation.
It enforces line-level syntax, structural constraints, and field-level quality rules.

#### `validate_see_also_authenticity.py`
**Purpose**: Detect synthetic or placeholder-like `see_also` NID patterns
**Usage**: `python scripts/validate_see_also_authenticity.py [--input <path>]`
**Default Targets** (first existing):
- `Outputs/06_words_final.md`
- `Outputs/05_see_also_fixed.md`
- `Outputs/04_see_also.md`

**Features**:
- Extracts NIDs only from `see_also:` sections inside strict `SSTART...EEND` blocks
- Flags suspicious placeholder prefix patterns (for example `nid1000000000...`)
- Detects long global consecutive NID runs (typical of fabricated sequences)
- Prints block-level hints for local consecutive runs
- Returns non-zero exit code when strong synthetic patterns are detected

#### `recover_missing_seealso.py`
**Purpose**: Automate the NW3/NW4 recovery loop when non-phrase entries are missing `see_also` or contain non-canonical `see_also` lines.
**Usage**:
- `python scripts/recover_missing_seealso.py`
- `python scripts/recover_missing_seealso.py --dry-run`

**What it does**:
- Reads `Outputs/06_words_final_fixed.md` and detects:
	- non-phrase entries that still lack `see_also`,
	- entries with non-canonical `see_also` syntax.
- Builds a targeted NotebookLM MCP query for only affected words
- Upserts `SSTART...EEND` blocks into `Outputs/04_see_also.md` by `word:`:
	- replaces existing blocks for repaired words,
	- appends blocks for new words.
- Rebuilds downstream outputs:
	- `Outputs/05_see_also_fixed.md`
	- `Outputs/06_words_final.md`
	- `Outputs/06_words_final_fixed.md`
- Repeats until missing coverage and non-canonical syntax are fully resolved or max rounds is reached

### Debug Utilities

#### `debug_tags.py`
**Purpose**: Debug and understand tag normalization process  
**Usage**: `python scripts/debug_tags.py`

**Features**:
- Step-by-step tag processing demonstration
- Useful for troubleshooting tag normalization
- Shows mapping and filtering rules in action

## Usage in Processing Pipeline

These scripts are used in the complete vocabulary processing workflow:

```bash
# Step 1: Generate vocabulary from word list (Requirement 1)
python scripts/process_requirement1.py

# Step 2: Validate completeness
python scripts/validate_word_list.py

# After Requirements 2-3 are complete:

# Step 3: Normalize see_also references (Requirement 4)
python scripts/process_requirement4.py

# Step 3.25: Recover missing/non-canonical see_also entries (if needed)
python scripts/recover_missing_seealso.py

# Step 3.5: Detect synthetic see_also NID patterns
python scripts/validate_see_also_authenticity.py

# Step 4: Authoritative NW4 validation
python scripts/validate_requirement4.py

# Optional quick diagnostic summary
python scripts/final_validate.py
```

## Output Files

- **Outputs/06_words_final_fixed.md**: Final vocabulary database ready for Anki import
- Processing logs and validation reports displayed in console

## Requirements

- Python 3.11+
- mdproc package installed (`pip install -e .` from Tools directory)
- Input files must exist in parent directory (German_New_Words/)
