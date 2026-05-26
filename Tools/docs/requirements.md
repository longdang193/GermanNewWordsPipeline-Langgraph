## Goal

Create a Python tool that reads a Markdown file, finds `SSTART … EEND` blocks, normalizes fields inside each block per rules, cleans spaces, and can output a deduplicated word list from the `word` field.

## Scope (In / Out)

- In: plain-text Markdown files encoded UTF-8; blocks delimited by lines exactly `SSTART` and `EEND`.
- Out:
	- (a) normalized Markdown with formatted blocks;
	- (b) extracted word list.
- Out of scope: fuzzy parsing, non-UTF-8 encodings, nested SSTART/EEND, streaming huge files.

## Interfaces / CLI / API

- Library API (preferred):

	```python
	def process_markdown(md: str) -> str: ...
	def extract_words(md: str) -> list[str]: ...
	```

* CLI:

	```
	mdproc process <input.md> [--output <out.md>]
	mdproc words <input.md> [--output <words.md>]
	```

	* `process` writes the normalized Markdown.
	* `words` writes a bullet list, one `- word` per line, in source order without duplicates.

## Data contracts

### Block detection

* A block starts at a line equal to `SSTART` and ends at the next line equal to `EEND` (inclusive).
* Inside a block: zero or more `FieldName: value` lines, possibly blank lines.

### Field normalization rules (applied to every block)

1. **noun_gender field**
	
	* Replace `(Plural)` or `(Pluralwort)` with `(plural)` (case-insensitive on the words `Plural` / `Pluralwort`).
	* Example: `noun_gender: die (Plural)` → `noun_gender: die (plural)`.

2. **Tags field**

	* Replace these punctuation characters with spaces everywhere in the Tags value:

		```
		(),:;=-*-+.\`\~"'?><|\[]{}\
		```

	* Normalize tag names (case-insensitive mapping of whole tokens):
		* `adjective` → `adj`
		* `adverb` → `adv`
		* `conjunction` → `conj`
		* `preposition` → `prep`
	* Keep only tags in this allowlist (drop others), case-insensitive, output lowercased, space/comma-insensitive:

		```
		verb, noun, adj, adv, phrase, conj, compound, interjection,
		modal, possessive, prefix, prep, pronoun
		```

	* Output formatting: `Tags: tag1 tag2` (space only between sorted unique tags).

3. **Whitespace cleanup**

	* Collapse internal runs of spaces to a single space within field values where sensible.
	* Trim trailing spaces on all lines.
	* Preserve original line breaks, but remove extra blank lines at the end of a block (max one blank line between fields).

### Example (expected)

Input block (abridged):

```
SSTART
%VOCAB (German) ver 3
word: Bauarbeiten
meaning: die Bauarbeiten = Arbeiten am Bau / construction work
de_1: Die Bauarbeiten auf der Straße dauern noch zwei Wochen.
en_1: The construction work on the street will last another two weeks.
word_inf: die Bauarbeiten
noun_gender: die (Plural)
noun_genetiv: -
noun_plural: Bauarbeiten
noun_forms: -
see_also:
arbeiten
Tags: Noun
EEND
```

Output block:

```
SSTART
%VOCAB (German) ver 3
word: Bauarbeiten
meaning: die Bauarbeiten = Arbeiten am Bau / construction work
de_1: Die Bauarbeiten auf der Straße dauern noch zwei Wochen.
en_1: The construction work on the street will last another two weeks.
word_inf: die Bauarbeiten
noun_gender: die (plural)
noun_genetiv: -
noun_plural: Bauarbeiten
noun_forms: -
see_also:
arbeiten
Tags: noun
EEND
```

### Word list extraction

* From all blocks, collect the value of the `word` field.
* Output as Markdown bullets, **deduplicated in first-seen order**:

	```
	- Bauarbeiten
	- arbeiten
	```

## Acceptance tests

1. Detects multiple `SSTART … EEND` blocks and leaves non-block text unchanged.
2. noun_gender normalization converts `(Plural|Pluralwort)` to `(plural)` case-insensitively.
3. Tags: punctuation replaced with spaces; tokens normalized (`adjective`→`adj`, etc.); allowlist enforced; output sorted unique lowercased tags as `Tags: tag1 tag2`.
4. Trims trailing spaces; collapses double spaces; removes extra blank lines inside blocks (no more than one between fields).
5. `extract_words` returns deduplicated words in source order.
6. CLI `process` and `words` produce expected files; no extra dependencies.

## Non-functional

* Performance: handle files up to 5 MB in <1s on a typical laptop.
* No network; standard library only.
* Deterministic output.

## Constraints

* Python 3.11
* Style: black; Lint: ruff; Types: mypy (strict where practical).

## Task 2025-09-29-11-28-14: Extend the Markdown Processor — merge `see_also`

### Library API

```python
def preprocess_file1(md: str) -> str:
    """Deduplicate by word (keep first), normalize whitespace in File 1."""
def merge_see_also(file1_md: str, file2_md: str) -> str:
    """Return File 2 after injecting deduped see_also from File 1 into matching word blocks."""
```

### CLI

```
mdproc preprocess <file1.md> [--output <file1_clean.md>]
mdproc merge-see-also <file1.md> <file2.md> [--output <out.md>]
```

### Behavior

* **Preprocess File 1**
	* Deduplicate by `word` (keep the **first** block, drop later duplicates).
	* Remove trailing spaces; collapse multiple spaces per line.
	* Normalize blank lines (no extra blank lines at block boundaries).
* **Merge `see_also` into File 2**
	* For each `word` present **and** having a `see_also` in File 1:
		* Find exact `word` match block in File 2.
		* Insert/append a `see_also` section:
			* **Placement**: above `Tags` if present; otherwise immediately above `EEND`.
			* **Deduplicate** within that block’s `see_also`, preserving first-seen order.

### Acceptance (extra)

* File 1 has no duplicate `word` blocks after preprocessing.
* File 1 has no trailing/double spaces after preprocessing.
* For each matching `word`, File 2 contains a `see_also` in the correct position.
* `see_also` lines are deduplicated, order-preserving.

