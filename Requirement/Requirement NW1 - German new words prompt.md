---
aliases: []
time: 2025-10-15-11-52
tags:
  - "#prompt"
  - "#language-german"
status: []
TARGET DECK: TEST
---

[[Requirement NW4 - Validate and Normalize see_also Anki References]].

## Objective

From [[Word List (DE)]] in `Inputs`, create **new enriched vocabulary files** inside `Outputs`.

## Current Project Structure (source of truth)

- Input list (SSOT): `Inputs/Word List (DE).md`
- NW1 generator: `py Tools/scripts/process_requirement1.py`
- NW1 validator (authoritative for completeness + placeholder bans): `py Tools/scripts/validate_word_list.py`
- Full pipeline runner (NW1→NW4): `py Tools/scripts/run_full_pipeline.py`
- Windows executable:
  - `dist/GermanNewWords/GermanNewWords.exe` (interactive menu, sets input list path + runs pipeline)
- Prompt SSOT files (used by automation):
  - `Prompt/nw1_enrich_system.txt`
  - `Prompt/nw1_enrich_instructions.md`

## Generality Requirement

The NW1 workflow must be input-agnostic and reusable for different future word lists:

* Do not assume a fixed number of entries.
* Do not assume a fixed topic/domain.
* Handle mixed content (single words, phrases, full sentences) from the current input file.
* Derive output coverage only from the current `Inputs/Word List (DE).md` content.
* Avoid hardcoded, list-specific lexical outputs in requirements logic.

## Inputs

* **Requirement file:** A list of German words or expressions from `Inputs/Word List (DE).md`.
* **POS detection:** automatically identify part of speech (noun, verb, adjective, phrase, etc.), correcting errors where necessary.

## Output

* **Destination folder:** `Outputs`
* **File name:** `Outputs/01_words.md`
* **Encoding:** UTF-8, Unix line endings.
* **Write mode:**
	* Always rebuild `Outputs/01_words.md` from scratch from the current `Inputs/Word List (DE).md`.
	* Do **not** append to an existing file.
	* Deduplicate entries only within the current run (case-insensitive).
* **Entry separator:** one blank line between entries.

## METADATA HEADER

Every generated file **must begin with** the following metadata block exactly as shown:

```
TARGET DECK: TEST
```

*(This header must appear **before any vocabulary entries**.)*

## Procedure

> NOTE: NW1 is implemented as an automated script (`Tools/scripts/process_requirement1.py`) and must remain input-agnostic.

1. **Read and preprocess the requirement file**

	* Load all lines, trimming leading and trailing whitespace.
	* Ignore blank lines and comments (lines beginning with `#`).
	* Normalize line endings to UTF-8 (Unix style).

2. **Extract entries and classify them**

	* Identify whether each entry is:
		* a **single lexical item** (noun/verb/adjective/adverb), or
		* a **phrase or sentence** (multiple words, expressions, or full clauses).
	* Keep the **original full text** exactly as written for later processing.

3. **Reorder entries**

	* **First group:** single lexical items (words).
	* **Second group:** phrases and sentences.
	* Within **each group**, sort entries **alphabetically (A–Z)** by their visible text (ignoring leading articles like *der*, *die*, *das* if present).
	- Resulting order:

		```
		[words A–Z]
		[phrases/sentences A–Z]
		```

	- Example:

		```
		Baustoffe
		Chemikalien
		Erdgas – natural gas
		Ich vermute, …
		Ich vermute, er kommt später.
		```

4. **Normalize entries**

	* Retain the **original full phrase** in the `WORD` field.
	* Remove appended meaning segments (e.g., `– to ...`, `— ...`) from `WORD`, but **reuse them** to populate the `MEANING` field.
	* Perform light normalization:
		* remove double spaces
		* fix casing
		* correct minor typos.

5. **Enrich phrases for clarity and natural use**

	* If a phrase is **too minimal**, **ambiguous**, or **lacking an object**, expand it to a more idiomatic expression.
	* Add natural complements (e.g., *etwas*, *jemanden*, *seine*, etc.).
	* Examples:
		* `dabei haben → dabei etwas haben`
		* `Hausaufgaben machen → seine Hausaufgaben machen`
		* `ausgeben für → Geld ausgeben für etwas`
		* `den Geburtstag feiern → seinen Geburtstag feiern`
		* `mit der Arbeit fertig sein → mit der Arbeit völlig fertig sein`
	* Ensure expressions sound **natural at CEFR B1–B2 level**.

6. **Identify part of speech (POS)**

	* Determine whether the entry is a **noun**, **verb**, or **other** (adjective/adverb/phrase).
	* Correct capitalization or misclassification before continuing.

7. **Apply the appropriate template**

	* Use the corresponding **noun**, **verb**, or **other** template.
	* Always include natural example sentences in:
		* `de_1`
		* `en_1`.
	* `de_1` and `en_1` must be authored as real usage examples, not produced from a generic sentence formula.

8. **Validate linguistic details**

	* **Nouns**
		* article
		* noun_gender
		* plural
		* Genitiv form
		* declension endings.
	* **Verbs**
		* 3rd person singular present
		* Präteritum
		* Perfekt (correct auxiliary *haben/sein*).
	* **Phrases/adjectives/adverbs**
		* syntactic correctness
		* idiomatic usage.

9. **Prevent duplication**

	* Deduplicate entries within the current run (case-insensitive match on `WORD`).
	* Do not use the previous output file as a source of truth for duplicate filtering.

10. **Write entries to the Markdown file**

* Write the validated entries in the **sorted order determined in Step 3**.
* Overwrite the previous `Outputs/01_words.md` file.
* Separate entries with **one blank line**.

11. **Append summary comment**

```
<!-- processed: N | added: M | skipped (duplicates): K -->
```

## Templates

### TEMPLATE for nouns

```
SSTART
%VOCAB (German) ver 3
word: [Word or phrase (removing the meaning part)]
meaning: [Word] = [simple German meaning(s)] / [English meaning(s)]
de_1: (Example sentence in German using the word/phrase)
en_1: (Translation of the example sentence)
word_inf: [include article + noun, e.g., "der Mann"]
noun_gender: [der/die/das/die (plural)]
noun_genetiv: [genetiv form]
noun_plural: [plural form]
noun_forms: [e.g., -es, ⸚er]
Tags: noun
EEND
```

### TEMPLATE for verbs

```
SSTART
%VOCAB (German) ver 3
word: [Word or phrase (removing the meaning part)]
meaning: [Word] = [simple German meaning(s)] / [English meaning(s)]
de_1: (Example sentence in German using the verb/phrase)
en_1: (Translation of the example sentence)
word_inf: [infinitive form]
verb_present: [3rd person singular present]
verb_past: [Präteritum]
verb_perfect: [Perfekt (correct auxiliary haben/sein)]
Tags: verb
EEND
```

### TEMPLATE for other (adjective/adverb/phrase/etc.)

```
SSTART
%VOCAB (German) ver 3
word: [Word or phrase (removing the meaning part)]
meaning: [Word] = [simple German meaning(s)] / [English meaning(s)]
de_1: (Natural example sentence)
en_1: (Translation)
word_inf: [lemma or canonical form]
Tags: [part of speech, e.g., adjective/adverb/phrase]
EEND
```

## Updated Rules

### WORD field

* **Keep the full original phrase** in `WORD`.
* Remove appended meanings (e.g., `– ...`) **only from the WORD field**, but reuse them when generating the `MEANING`.
* `WORD` must never contain parenthetical meaning/gloss text.
	* Invalid: `word: bestehen (pass, overcome)`
	* Valid: `word: bestehen`
* For **noun entries**, `WORD` must not include a leading article (`der`, `die`, `das`).
	* Invalid: `word: das Aufregendste`
	* Valid: `word: Aufregendste`
	* Put the article in `word_inf` / `noun_gender`, not in `WORD`.

### MEANING format

`MEANING` must always follow this format:

```
meaning: [Word] = [German meaning(s)] / [English meaning(s)]
```

Example:

```
meaning: Baustoff = Material zum Bauen von Häusern / building material
meaning: vermuten = denken, dass etwas wahrscheinlich ist / to suppose, to assume
meaning: fertig sein mit der Arbeit = seine Arbeit komplett beendet haben / to be finished with work
```

Requirements:

* **German meaning must come first.**
* German meanings must be **simple, clear, and understandable for CEFR B1 learners**.
* Avoid complex academic wording.
* Prefer **short explanatory phrases** instead of synonyms if needed.

Example:

Good (B1-friendly)

```
denken, dass etwas wahrscheinlich ist
```

Less good

```
eine Hypothese formulieren
```

### Multiple meanings

If several meanings exist:

```
meaning: Wort = Bedeutung1; Bedeutung2 / meaning1; meaning2
```

Example:

```
meaning: ausgeben = Geld bezahlen; Geld für etwas verwenden / to spend money
```

### Context sentences

Always include:

```
de_1
en_1
```

Requirements:

* `de_1` must sound **natural and typical for B1–B2 German**.
* `en_1` must be **clear and close to the original meaning**.
* Both lines must be **lexically and grammatically plausible for the specific entry**.
* A sentence must not merely insert the target entry into a generic shell.

Example:

```
de_1: Er gibt viel Geld für Bücher aus.
en_1: He spends a lot of money on books.
```

### Noun rules

* `word_inf` must include the article (**der/die/das**).
* `noun_gender` must always be filled:

```
der
die
das
die (plural)
```

If variable:

```
der/die
die/das
```

**noun_forms encoding**

Unchanged endings

```
-es
-n
-s
```

Umlaut changes

```
⸚er
⸚e
```

Example

```
Mann → Männer → ⸚er
```

Singular-only nouns

```
-, 
```

### Verb rules

* `word_inf` = infinitive
* Fill:

```
verb_present: [3rd person singular present]
verb_past: [Präteritum]
verb_perfect: [Perfekt (correct auxiliary haben/sein)]
```

Example:

```
word_inf: vermuten
verb_present: vermutet
verb_past: vermutete
verb_perfect: hat vermutet
```

### Other POS

For adjectives/adverbs/phrases:

* Fill `word_inf`
* Skip noun/verb-specific fields.

Example:

```
Tags: phrase
```

### Correction rule

If the input list contains mistakes, **fix them automatically**, including:

* spelling
* capitalization
* incorrect POS
* wrong grammar forms

### Naturalness rule

Before writing entries:

* ensure `de_1` sounds **native-like**
* ensure `en_1` **clearly illustrates the meaning**

Target level:

```
German: CEFR B1–B2
```

### Speaking-oriented example rule

`de_1` must be **speaking-oriented**, meaning learners should be able to **use the sentence directly in conversation**.

Preferred characteristics:

* **Common everyday situations**
* **Short and natural spoken German**
* **Useful conversation patterns**

Good examples:

```
Ich vermute, er kommt später.
```

```
Ich brauche heute Erdgas für die Heizung.
```

```
Ich gebe heute nicht so viel Geld aus.
```

Less suitable examples:

```
Die Analyse des Energieverbrauchs zeigt einen Anstieg.
```

```
Baustoffe werden häufig im Bauwesen verwendet.
```

### LLM-authored example rule

`Outputs/01_words.md` must be produced from **real semantic generation**, not from placeholder expansion or deterministic fallback formulas.

Requirements:

* Treat each entry as an LLM-authored mini lexicographic task.
* Generate a **specific, concrete, believable** usage context for each entry.
* Do **not** use sentence shells such as:

```
Bei diesem Thema spielt [WORD] eine wichtige Rolle.
```

```
[WORD] plays an important role in this topic.
```

```
Im Arbeitsalltag brauchen wir [WORD] regelmässig.
```

```
We regularly need [WORD] in everyday work.
```

* Do **not** use any equivalent formula that could fit dozens of unrelated entries with simple substitution.
* If a suitable natural example cannot be generated confidently, **skip the entry** and report it as unresolved instead of fabricating a dummy sentence.

### Anti-placeholder rule

`meaning`, `de_1`, and `en_1` must contain **real linguistic content**, never meta-descriptions or template filler.

**Forbidden patterns** (these must never appear in output):

| Field | Forbidden pattern |
|-------|-------------------|
| `meaning` | `= konkrete Bedeutung im aktuellen Themenfeld` |
| `meaning` | `= konkrete Formulierung im Themenfeld` |
| `meaning` | `= Nomen im Themenkontext` |
| `meaning` | `= Verb fuer Handlung im Kontext` |
| `de_1` | `Im Text kommt [WORD] mehrmals vor.` |
| `de_1` | `Im Unterricht besprechen wir [WORD].` |
| `de_1` | `Wir setzen das Wort [WORD] in einem klaren Satz ein.` |
| `de_1` | `[WORD] taucht in diesem Abschnitt mehrfach auf.` |
| `de_1` | `Bei diesem Thema spielt [WORD] eine wichtige Rolle.` |
| `de_1` | `Im Arbeitsalltag brauchen wir [WORD] regelmässig.` |
| `en_1` | `The word [WORD] appears several times in the text.` |
| `en_1` | `In class, we discuss [WORD].` |
| `en_1` | `We use the word [WORD] in a clear sentence.` |
| `en_1` | `This term appears several times in this section.` |
| `en_1` | `This sentence pattern is used to describe sequence and timing.` |
| `en_1` | `[WORD] plays an important role in this topic.` |
| `en_1` | `We regularly need [WORD] in everyday work.` |

**Rules:**

* `meaning` must contain a **real definition** that a B1 learner can understand, not a meta-description about the word's role in a text.
* `de_1` must be a **real example sentence** where the word is used in a natural everyday context.
* `en_1` must be a **translation of the example sentence**, not a description of the word.
* `de_1` and `en_1` must never be dummy compliance sentences that are only technically valid because they contain the target text.
* If you **cannot determine the actual meaning** of a word, **skip the entry** and list it in a separate `<!-- UNRESOLVED: word1, word2 -->` comment at the bottom of the file.

## Input Line Formats (supported)

NW1 input accepts mixed content and derives meaning hints when present:

- Case 1: word only (no meaning): `Gleiche`
- Case 2: word + meaning:
  - `Bedrohungen (threat)`
  - `**Bedrohungen** - threat`
  - `Bedrohungen = threat`
- Case 3: phrase, with or without meaning
- Case 4: sentence, with or without meaning

Rule: if no meaning hint exists, automation uses LLM enrichment (SSOT prompt in `Prompt/`) rather than deterministic placeholders.
