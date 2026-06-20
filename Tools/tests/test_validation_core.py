from __future__ import annotations

import textwrap

from mdproc.validation_core import (
    analyze_block_structure,
    extract_block_see_also_entries,
    iter_blocks,
    iter_see_also_entries,
    validate_no_blank_lines_between_fields,
    validate_meaning_field_rules,
    validate_placeholder_values,
    validate_required_core_fields,
    validate_single_word_requires_see_also,
    validate_tags_last,
    validate_unique_fields_per_block,
    validate_word_field_rules,
)


def dedent(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n").rstrip("\n")


def test_analyze_block_structure_flags_legacy_markers():
    lines = dedent(
        """
        START
        word: Test
        END
        """
    ).splitlines()

    count, issues = analyze_block_structure(lines)

    assert count == 0
    assert any("Invalid block indicators found" in issue for issue in issues)
    assert any("No SSTART...EEND blocks found" in issue for issue in issues)


def test_iter_see_also_entries_stops_at_next_field():
    lines = dedent(
        """
        SSTART
        word: Ablauf
        see_also:
        der [Prozess|nid1] = process
        [Sequenz|nid2] = sequence
        Tags: noun
        EEND
        """
    ).splitlines()

    block = next(iter(iter_blocks(lines)))
    assert extract_block_see_also_entries(block) == [
        "der [Prozess|nid1] = process",
        "[Sequenz|nid2] = sequence",
    ]
    assert iter_see_also_entries(lines) == [
        "der [Prozess|nid1] = process",
        "[Sequenz|nid2] = sequence",
    ]


def test_validate_placeholder_values_reports_template_text():
    lines = dedent(
        """
        SSTART
        word: Ablauf
        meaning: [simple German meaning]
        de_1: Das ist ein Ablauf.
        en_1: This is a process.
        Tags: noun
        EEND
        """
    ).splitlines()

    issues = validate_placeholder_values(lines)

    assert issues == [
        "Line 3: Placeholder text detected in field 'meaning' -> '[simple German meaning]'"
    ]


def test_validate_required_core_fields_uses_shared_block_parser():
    lines = dedent(
        """
        SSTART
        word: Ablauf
        meaning:
        de_1: Das ist ein Ablauf.
        Tags: noun
        EEND
        """
    ).splitlines()

    issues = validate_required_core_fields(lines)

    assert "required field 'meaning' is empty" in issues[0]
    assert "missing required field 'en_1'" in issues[1]


def test_validate_word_field_rules_rejects_parenthetical_gloss_and_noun_article():
    lines = dedent(
        """
        SSTART
        word: der Ablauf (process)
        meaning: Ablauf / process
        de_1: Der Ablauf ist klar.
        en_1: The process is clear.
        Tags: noun
        EEND
        """
    ).splitlines()

    issues = validate_word_field_rules(lines)

    assert len(issues) == 2
    assert "must not include parenthetical meaning/gloss" in issues[0]
    assert "must not start with der/die/das" in issues[1]


def test_validate_meaning_field_rules_rejects_noun_without_article_and_circular_gloss():
    lines = dedent(
        """
        SSTART
        word: Meeresspiegel
        meaning: Meeresspiegel = Meeresspiegel / sea level
        de_1: Der Meeresspiegel steigt langsam.
        en_1: Sea level is rising slowly.
        word_inf: der Meeresspiegel
        noun_gender: der
        noun_genetiv: des Meeresspiegels
        noun_plural: -
        noun_forms: -s, -
        Tags: noun
        EEND
        """
    ).splitlines()

    issues = validate_meaning_field_rules(lines)

    assert any("noun meaning must start with article-bearing lemma" in issue for issue in issues)
    assert any("noun meaning gloss must not repeat the noun itself" in issue for issue in issues)


def test_validate_single_word_requires_see_also_exempts_phrase_blocks():
    lines = dedent(
        """
        SSTART
        word: Ablauf
        meaning: Ablauf / process
        de_1: Der Ablauf ist klar.
        en_1: The process is clear.
        Tags: noun
        EEND
        SSTART
        word: nach wie vor
        meaning: nach wie vor / still
        de_1: Das gilt nach wie vor.
        en_1: That still applies.
        Tags: phrase
        EEND
        """
    ).splitlines()

    issues = validate_single_word_requires_see_also(lines)

    assert issues == [
        "Line 2: non-phrase block 'Ablauf' must contain a non-empty see_also field"
    ]


def test_validate_tags_last_rejects_fields_after_tags():
    lines = dedent(
        """
        SSTART
        word: Ablauf
        meaning: Ablauf / process
        de_1: Der Ablauf ist klar.
        en_1: The process is clear.
        Tags: noun
        see_also:
        der [Prozess|nid1] = process
        EEND
        """
    ).splitlines()

    issues = validate_tags_last(lines)

    assert issues == [
        "Line 6: Tags field must be the last field before EEND in block 'Ablauf'"
    ]


def test_validate_no_blank_lines_between_fields_rejects_separators():
    lines = dedent(
        """
        SSTART
        word: Ablauf
        de_1: Der Ablauf ist klar.

        en_1: The process is clear.
        Tags: noun
        EEND
        """
    ).splitlines()

    issues = validate_no_blank_lines_between_fields(lines)

    assert issues == [
        "Line 4: blank lines are not allowed between fields in block 'Ablauf'"
    ]


def test_validate_requirement4_handles_umlaut_only_plural_noun_forms():
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from validate_requirement4 import validate_blank_fields_and_noun_forms

    lines = dedent(
        """
        SSTART
        word: Mangel
        meaning: Mangel = Fehler / defect
        de_1: Den Mangel müssen wir dem Händler sofort melden.
        en_1: We need to report the defect to the dealer right away.
        word_inf: der Mangel
        noun_gender: der
        noun_genetiv: des Mangels
        noun_plural: Mängel
        noun_forms: -s, ⸚
        Tags: noun
        EEND
        """
    ).splitlines()

    issues = validate_blank_fields_and_noun_forms(Path("dummy"), lines)

    assert issues == []


def test_validate_unique_fields_per_block_rejects_merged_block_shape():
    lines = dedent(
        """
        SSTART
        %VOCAB (German) ver 3
        word: dürfte ich mal kurz stören?
        meaning: dürfte ich mal kurz stören? = höfliche Frage / may I disturb you for a moment?
        %VOCAB (German) ver 3
        word: Verträge
        word_inf: dürfte ich mal kurz stören
        Tags: phrase
        EEND
        """
    ).splitlines()

    issues = validate_unique_fields_per_block(lines)

    assert any("duplicate %VOCAB header" in issue for issue in issues)
    assert any("duplicate field 'word'" in issue for issue in issues)


def test_nw1_qa_detects_mixed_language_de1() -> None:
    from gnw_pipeline.nw1_qa import detect_mixed_language_de1

    issues = detect_mixed_language_de1("We need to feed die Katze.")
    assert issues
    assert issues[0].code == "mixed_language_de1"


def test_looks_like_noun_candidate_rejects_sentence_like_phrase() -> None:
    from mdproc.validation_core import looks_like_noun_candidate

    assert looks_like_noun_candidate("Setzen Sie sich doch") is False


def test_validate_requirement4_diacritics_allows_zue_prefix_words() -> None:
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from validate_requirement4 import validate_german_diacritics

    lines = dedent(
        """
        SSTART
        word: zuerst
        meaning: zuerst = first
        de_1: Zuerst essen wir.
        en_1: First we eat.
        Tags: adverb
        see_also:
        [zuerst|nid1] = first
        EEND
        """
    ).splitlines()

    assert validate_german_diacritics(lines) == []


def test_validate_requirement4_diacritics_allows_tagesaktuell() -> None:
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from validate_requirement4 import validate_german_diacritics

    lines = dedent(
        """
        SSTART
        word: derzeit
        meaning: derzeit = zurzeit / currently
        de_1: Derzeit arbeite ich im Homeoffice.
        en_1: Currently I work from home.
        Tags: adv
        see_also:
        [tagesaktuell|nid1] = current, up-to-date
        EEND
        """
    ).splitlines()

    assert validate_german_diacritics(lines) == []
