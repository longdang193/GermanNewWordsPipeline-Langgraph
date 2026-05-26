from __future__ import annotations
import textwrap
from mdproc.core import process_markdown, extract_words
from scripts.process_requirement1 import GermanVocabProcessor


def dedent(s: str) -> str:
    return textwrap.dedent(s).lstrip("\n").rstrip() + "\n"


def test_basic_block_formatting():
    src = dedent(
        """
        SSTART
    word: Bauarbeiten
    meaning: die Bauarbeiten = construction work  
    noun_gender: die (Plural)
    Tags: Noun  ,   adjective;unknown
        EEND
    """
    )
    out = process_markdown(src)
    assert "word: Bauarbeiten" in out
    assert "noun_gender: die (plural)" in out
    assert "Tags: adj noun" in out  # normalized, allowlisted, sorted
    # trailing spaces removed
    for line in out.splitlines():
        assert not line.endswith(" ")


def test_multiple_blocks_and_nonblock_text():
    src = dedent(
        """
    Title

        SSTART
    word: A
    Tags: verb, Conjunction
        EEND

    some paragraph

        SSTART
    word: B
    Tags: adjective/participle
        EEND
    """
    )
    out = process_markdown(src)
    # Non-block text preserved
    assert "Title" in out and "some paragraph" in out
    # Tags normalized and filtered
    assert "Tags: conj verb" in out
    assert "Tags: adj" in out


def test_gender_pluralwort():
    src = dedent(
        """
        SSTART
    word: X
    noun_gender: die (Pluralwort)
        EEND
    """
    )
    out = process_markdown(src)
    assert "noun_gender: die (plural)" in out


def test_word_extraction_dedup_order():
    src = dedent(
        """
        SSTART
    word: A
        EEND

        SSTART
    word: B
        EEND

        SSTART
    word: A
        EEND
    """
    )
    words = extract_words(src)
    assert words == ["A", "B"]


def test_tags_punctuation_replaced():
    src = dedent(
        r"""
        SSTART
    word: foo
    Tags: adjective(),:;=-*-+.`~"'?><|\[]{}  noun
        EEND
    """
    )
    out = process_markdown(src)
    assert "Tags: adj noun" in out


def test_parse_entry_keeps_parenthetical_gloss_as_meaning():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]
    word, meaning = processor.parse_entry("**Abläufe (processes/workflows)**")
    assert word == "Abläufe"
    assert meaning == "processes/workflows"


def test_fallback_entry_with_meaning_avoids_generic_quality_markers():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]
    entry = processor.generate_noun_entry("Abläufe", "processes/workflows")
    issues = processor.validate_entry_quality(entry)
    assert issues == []
