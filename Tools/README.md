# German New Words - Tools and Processing Pipeline

A comprehensive toolkit for processing German vocabulary Markdown files with structured vocabulary entries in `SSTART...EEND` blocks. This toolkit supports the complete workflow from raw word lists to normalized, cross-referenced Anki-ready vocabulary databases.

## Overview

This project provides tools and scripts to process German vocabulary through a 4-requirement pipeline:

1. **Requirement 1**: Create enriched vocabulary entries from raw word lists
2. **Requirement 2**: Normalize vocabulary fields and extract word lists  
3. **Requirement 3**: Merge see_also cross-references into final vocabulary database
4. **Requirement 4**: Validate and normalize Anki references

## Features

### Core mdproc Library
- **Field Normalization**: Automatically normalizes `noun_gender`, `Tags`, and other fields according to predefined rules
- **Tag Management**: Maps synonymous tags (e.g., `adjective` → `adj`), enforces an allowlist, and sorts tags
- **Gender Normalization**: Converts `(Plural)` and `(Pluralwort)` to standardized `(plural)` format in `noun_gender` field
- **Word Extraction**: Extracts deduplicated word lists from vocabulary blocks
- **See Also Merging**: Merges cross-reference (`see_also`) fields between files
- **Whitespace Cleanup**: Removes trailing spaces, collapses multiple spaces, and normalizes blank lines

### Processing Scripts
- **Requirement Processing**: Specialized scripts for each processing requirement
- **Validation Tools**: Syntax validation and quality assurance utilities
- **Debug Utilities**: Tools for troubleshooting and development

## Quick Start - Complete Processing Workflow

### Processing Pipeline Overview

The complete vocabulary processing workflow follows this sequence:

```
Inputs/Word List (DE).md → Req NW1 → Req NW2 → Req NW3 → Req NW4 → Final Database
      ↓                    ↓         ↓         ↓         ↓
   Source terms         Outputs/01  Outputs/03  Outputs/06  Outputs/06_words_final_fixed.md
            _words.md   _word_list.md _words_final.md
```

### Step-by-Step Processing

1. **Requirement 1**: 
   - Generate vocabulary: `python scripts/process_requirement1.py`
   - Reads terms from `Inputs/Word List (DE).md` (or legacy inline Word List in Requirement NW1)
   - Creates `Outputs/01_words.md` with ver 3 formatted entries (lowercase fields)
2. **Requirement 2**: 
   - **Validate first**: `python scripts/validate_word_list.py`
   - If validation passes: `py -m mdproc process Outputs/01_words.md --output Outputs/02_words_fixed.md`
   - Generate word list: `py -m mdproc words Outputs/02_words_fixed.md --output Outputs/03_word_list.md`
   - If validation fails: Regenerate `Outputs/01_words.md` via Requirement NW1
3. **Requirement 3**: 
   - Generate `Outputs/04_see_also.md` via NotebookLM MCP using `Outputs/03_word_list.md`
   - `py -m mdproc preprocess Outputs/04_see_also.md --output Outputs/05_see_also_fixed.md`
   - `py -m mdproc merge-see-also Outputs/05_see_also_fixed.md Outputs/02_words_fixed.md --output Outputs/06_words_final.md`
4. **Requirement 4**:
   - `python scripts/process_requirement4.py`
   - `python scripts/recover_missing_seealso.py` (run if NW4 reports missing non-phrase `see_also` or non-canonical `see_also` syntax)
   - `python scripts/validate_requirement4.py` (authoritative NW4 gate)
   - `python scripts/final_validate.py` (optional quick diagnostic summary)

### Final Output
- **Outputs/06_words_final_fixed.md**: Complete, normalized vocabulary database ready for Anki import

## Installation

### Prerequisites

- Python 3.11 or higher
- Make (optional, for using the Makefile)

### Install from Source

1. Clone or navigate to the repository
2. Install the package in development mode:

**Using Make (Unix/Linux/macOS):**

```bash
make install
```

**Using PowerShell (Windows):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e ".[dev]"
```

**Manual installation:**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"
```

## Usage

### Command-Line Interface

The tool provides four main commands:

#### Process - Normalize Markdown Blocks

Normalizes all `SSTART...EEND` blocks in a Markdown file:

```bash
mdproc process input.md --output output.md
```

**Example transformation:**

```markdown
# Input
SSTART
%word: Bauarbeiten
noun_gender: die (Plural)
Tags: Noun, adjective; compound
EEND

# Output
SSTART
%word: Bauarbeiten
noun_gender: die (plural)
Tags: adj compound noun
EEND
```

#### Words - Extract Word List

Extracts a deduplicated list of words from all blocks:

```bash
mdproc words input.md --output words.md
```

**Output format:**

```markdown
- Bauarbeiten
- arbeiten
- aufbauen
```

### Requirement Processing Scripts

#### validate_word_list.py

Validates that `Outputs/01_words.md` contains all words from Requirement NW1's source list:

```bash
python scripts/validate_word_list.py
```

**What it does:**
- Extracts terms from Requirement NW1 inline `## Word List` (legacy) or `Inputs/Word List (DE).md`
- Deduplicates words in the list (case-insensitive)
- Counts unique words/phrases in the Word List
- Counts strict SSTART...EEND blocks in `Outputs/01_words.md`
- Rejects legacy START...END block markers
- Rejects unreplaced template placeholders (for example: `[simple German meaning(s)]`, `[form]`)
- Compares counts to ensure completeness

**Exit codes:**
- `0` = Validation passed (all words processed)
- `1` = Validation failed (missing entries or file not found)

**When to use:**
- Before running Requirement 2 (mandatory validation step)
- After regenerating `Outputs/01_words.md` to verify completeness
- When troubleshooting missing vocabulary entries

#### process_requirement4.py

Normalizes and validates `see_also` Anki references to ensure they follow canonical syntax:

```bash
python scripts/process_requirement4.py
```

**What it does:**
- Ensures proper bracket completion: `[word|nid123]`
- Cleans NID formatting (removes `<>` characters)
- Preserves gender markers with correct spacing: `der [word|nid123]`
- Normalizes whitespace and formatting
- Validates strict block markers (`SSTART...EEND`) before processing

#### final_validate.py

Optional quick validation utility for checking processed files:

```bash  
python scripts/final_validate.py
```

**Role:** Fast human-readable diagnostics (counts, samples, basic formatting checks).
Use this for quick inspection, not as the final pass/fail gate.

#### validate_requirement4.py

Authoritative comprehensive validation with detailed error reporting:

```bash
python scripts/validate_requirement4.py
```

**Role:** Single authoritative NW4 pass/fail validator used by automation.
It enforces line-level syntax, structural constraints, and field-level quality rules.

#### recover_missing_seealso.py

Automates recovery for both missing and non-canonical `see_also` entries:

```bash
python scripts/recover_missing_seealso.py
```

Useful options:

```bash
python scripts/recover_missing_seealso.py --dry-run
python scripts/recover_missing_seealso.py --max-rounds 5
```

This script:
- Detects non-phrase words missing `see_also` in `Outputs/06_words_final_fixed.md`
- Detects words containing non-canonical `see_also` lines (for example missing `= meaning`)
- Queries NotebookLM MCP only for affected words
- Upserts `Outputs/04_see_also.md` by `word:` (replace existing blocks for repaired words, append new blocks for new words)
- Rebuilds `Outputs/05_see_also_fixed.md`, `Outputs/06_words_final.md`, and `Outputs/06_words_final_fixed.md`

#### Preprocess - Clean File 1

Deduplicates blocks by `word` (keeping first occurrence) and normalizes whitespace:

```bash
mdproc preprocess file1.md --output file1_clean.md
```

#### Merge See Also - Merge Cross-References

Merges `see_also` fields from File 1 into matching blocks in File 2:

```bash
mdproc merge-see-also file1.md file2.md --output merged.md
```

### Python API

#### Import the library

```python
from mdproc.core import process_markdown, extract_words, preprocess_file1, merge_see_also
```

#### Process and normalize markdown

```python
with open('input.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

normalized = process_markdown(md_content)

with open('output.md', 'w', encoding='utf-8') as f:
    f.write(normalized)
```

#### Extract word list

```python
with open('input.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

words = extract_words(md_content)
print(words)  # ['Bauarbeiten', 'arbeiten', ...]
```

## Block Format

### Standard Block Structure (ver 3)

```markdown
SSTART
%VOCAB (German) ver 3
word: <word>
meaning: <word> = <German meaning> / <English meaning>
de_1: <German example sentence>
en_1: <English translation>
word_inf: <infinitive/base form with article for nouns>
noun_gender: <der/die/das/die (plural)>  # for nouns
noun_genetiv: <genitive form>            # for nouns
noun_plural: <plural form>               # for nouns
noun_forms: <declension endings>         # for nouns
verb_present: <3rd person singular>      # for verbs
verb_past: <Präteritum>                  # for verbs
verb_perfect: <Perfekt with auxiliary>   # for verbs
see_also:
<related word 1>
<related word 2>
Tags: <tag1> <tag2>
EEND
```

### Field Normalization Rules

#### word Field

- Lowercase field name: `word:`
- Value is preserved as-is
- Used for deduplication (case-insensitive)

#### meaning Field

- Format: `word = German meaning / English meaning`
- German meaning comes first (B1-friendly)
- Multiple meanings separated by semicolons

#### noun_gender Field

- `(Plural)` or `(Pluralwort)` → `(plural)` (case-insensitive)
- Example: `die (Plural)` → `die (plural)`

#### Tags Field

Punctuation characters `(),:;=-*-+.`~"'?><|[]{}\/\` are replaced with spaces, then:

- **Tag Mapping** (case-insensitive):
	- `adjective` → `adj`
	- `adverb` → `adv`
	- `conjunction` → `conj`
	- `preposition` → `prep`
- **Allowlist** (only these tags are kept):
	- `verb`, `noun`, `adj`, `adv`, `phrase`, `conj`, `compound`, `interjection`, `modal`, `possessive`, `prefix`, `prep`, `pronoun`
- **Output**: Sorted, unique, lowercase tags separated by spaces

#### Whitespace

- Trailing spaces are removed from all lines
- Multiple consecutive spaces are collapsed to single space
- Maximum one blank line between fields

## Development

### Project Structure

```
Tools/
├── src/
│   └── mdproc/              # Core processing library
│       ├── __init__.py
│       ├── __main__.py      # CLI entry point
│       └── core.py          # Core processing logic
├── scripts/                 # Requirement processing scripts
│   ├── process_requirement1.py    # Generate vocab from word list
│   ├── validate_word_list.py      # Validate Requirement 1 completeness
│   ├── process_requirement4.py    # Normalize see_also references
│   ├── validate_requirement4.py   # Authoritative Requirement 4 validation
│   ├── final_validate.py          # Optional quick validation utility
│   └── debug_tags.py              # Debug utility for tags
├── tests/                   # Unit tests
│   ├── test_processor.py    # Unit tests for processing
│   └── test_merge.py        # Unit tests for merging
├── docs/                    # Documentation
│   ├── requirements.md      # Functional requirements
│   └── test_preprocess.md   # Test specifications
├── pyproject.toml           # Project configuration
├── Makefile.mak             # Build automation
└── README.md                # This file
```

### Running Tests

**Using Make:**

```bash
make test
```

**Using pytest directly:**

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pytest -q --maxfail=1 --disable-warnings --cov=src --cov-report=term-missing
```

### Code Quality

The project uses several tools to maintain code quality:

**Format code:**

```bash
make fmt          # Runs black
```

**Lint code:**

```bash
make lint         # Runs ruff
```

**Type check:**

```bash
make type         # Runs mypy
```

**Run all checks:**

```bash
make ci           # Runs fmt, lint, type, test
```

### Development Tools

- **black**: Code formatter (line length: 100)
- **ruff**: Fast Python linter
- **mypy**: Static type checker (strict mode)
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting

## Configuration

Configuration is managed through `pyproject.toml`:

- **Python Version**: 3.11+
- **Line Length**: 100 characters
- **Type Checking**: Strict mode enabled

## Debug Utilities

### debug_tags.py

A standalone script for debugging tag normalization:

```bash
python scripts/debug_tags.py
```

This script demonstrates step-by-step how tags are processed, useful for understanding or troubleshooting tag normalization behavior.

## Documentation

### docs/requirements.md
Detailed functional and technical requirements for the vocabulary processing system.

### docs/test_preprocess.md  
Test specifications and preprocessing documentation.

### Requirement Documents
Located in the parent `Requirement/` directory:
- `Requirement NW1 - German new words prompt.md`
- `Requirement NW2 - Validate and Normalize Vocabulary Fields.md`
- `Requirement NW3 - Merge see_also Cross-References into Final Vocabulary Database.md`
- `Requirement NW4 - Validate and Normalize see_also Anki References.md`

## Requirements

See `requirements.md` for detailed functional and technical requirements.

## Performance

- Handles files up to 5 MB in under 1 second on typical hardware
- No network dependencies
- Deterministic output (same input always produces same output)
- Standard library only (no external runtime dependencies)

## License

See project root for license information.

## Contributing

1. Install development dependencies: `make install` or `pip install -e ".[dev]"`
2. Make your changes
3. Run code quality checks: `make ci`
4. Ensure all tests pass
5. Submit your changes

## File Processing Examples

### Example: Complete Processing Workflow

```bash
# Requirement 2: Normalize fields
py -m mdproc process Outputs/01_words.md --output Outputs/02_words_fixed.md
py -m mdproc words Outputs/02_words_fixed.md --output Outputs/03_word_list.md

# Requirement 3: Generate and merge cross-references
# (Generate Outputs/04_see_also.md via NotebookLM MCP + prompt first)
py -m mdproc preprocess Outputs/04_see_also.md --output Outputs/05_see_also_fixed.md
py -m mdproc merge-see-also Outputs/05_see_also_fixed.md Outputs/02_words_fixed.md --output Outputs/06_words_final.md

# Requirement 4: Validate Anki references
python scripts/process_requirement4.py
python scripts/validate_requirement4.py
# Optional quick diagnostic summary
python scripts/final_validate.py
```

### Expected File Outputs

- **Inputs/Word List (DE).md**: Source terms for Requirement NW1
- **Outputs/01_words.md**: Raw enriched vocabulary entries
- **Outputs/02_words_fixed.md**: Normalized vocabulary fields
- **Outputs/03_word_list.md**: Extracted deduplicated word list
- **Outputs/04_see_also.md**: Cross-reference data generated via NotebookLM MCP
- **Outputs/05_see_also_fixed.md**: Cleaned cross-references
- **Outputs/06_words_final.md**: Complete vocabulary with cross-references
- **Outputs/06_words_final_fixed.md**: Final Anki-ready database

## Support

For detailed requirements and specifications, see:

- `docs/requirements.md` - Functional requirements and acceptance criteria
- `docs/test_preprocess.md` - Test specifications
- `../Requirement/` - Complete requirement documentation

