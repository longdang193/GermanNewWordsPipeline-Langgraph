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
    entry = dedent(
        """
        SSTART
        %VOCAB (German) ver 3
        word: Meeresspiegel
        meaning: der Meeresspiegel = die durchschnittliche Höhe vom Meer, von der aus man Höhen misst / sea level
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
    ).strip()
    issues = processor.validate_entry_quality(entry)
    assert issues == []


def test_noun_ending_in_en_does_not_use_verb_example_fallback():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]

    try:
        processor.generate_noun_entry("Wesen", "beings / creatures")
    except ValueError as exc:
        assert "Missing LLM-authored German example for 'Wesen'" in str(exc)
    else:
        raise AssertionError("Expected noun fallback to reject generic verb-style examples for 'Wesen'.")


def test_bare_infinitive_verb_does_not_use_generic_planning_example():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]

    try:
        processor.generate_verb_entry("trudeln", "to trickle in / arrive slowly and gradually")
    except ValueError as exc:
        assert "Missing LLM-authored German example for 'trudeln'" in str(exc)
    else:
        raise AssertionError("Expected verb fallback to reject generic planning example for 'trudeln'.")


def test_validate_entry_quality_rejects_circular_noun_meaning():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]
    entry = dedent(
        """
        SSTART
        %VOCAB (German) ver 3
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
    ).strip()

    issues = processor.validate_entry_quality(entry)

    assert any("noun meaning must start with article-bearing lemma" in issue for issue in issues)
    assert any("noun meaning gloss must not repeat the noun itself" in issue for issue in issues)


def test_english_only_meaning_hint_requires_llm_authored_meaning():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]

    try:
        processor.build_meaning_text("das Referat halten", "to give a presentation")
    except ValueError as exc:
        assert "Missing LLM-authored meaning for 'das Referat halten'" in str(exc)
    else:
        raise AssertionError("Expected English-only meaning hints to be rejected and rerouted to LLM authoring.")


def test_build_override_entry_normalizes_noun_meaning_lhs_to_word_inf():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]
    override = {
        "tags": "noun",
        "meaning": "Höhlenmenschen = Menschen aus der Steinzeit, die in Höhlen leben / cave people",
        "de_1": "Die Höhlenmenschen lebten in einfachen Behausungen.",
        "en_1": "The cave dwellers lived in simple shelters.",
        "word_inf": "der Höhlenmensch",
        "noun_gender": "der",
        "noun_genetiv": "des Höhlenmenschen",
        "noun_plural": "Höhlenmenschen",
        "noun_forms": "-en, -en",
    }

    entry = processor.build_override_entry("Höhlenmenschen", override)

    assert "meaning: der Höhlenmensch = Menschen aus der Steinzeit, die in Höhlen leben / cave people" in entry


def test_build_override_entry_adds_missing_meaning_lhs_for_phrase():
    processor = GermanVocabProcessor(requirement_file="dummy", output_file="dummy")  # type: ignore[arg-type]
    override = {
        "tags": "phrase",
        "meaning": "etwas macht einen bestimmten Prozentsatz der Note aus / something makes up a certain percent of the grade",
        "de_1": "Die Hausaufgaben machen zehn Prozent der Note aus.",
        "en_1": "The homework makes up ten percent of the grade.",
        "word_inf": "etwas macht … Prozent der Note aus",
    }

    entry = processor.build_override_entry("etwas macht … Prozent der Note aus", override)

    assert "meaning: etwas macht … Prozent der Note aus = etwas macht einen bestimmten Prozentsatz der Note aus / something makes up a certain percent of the grade" in entry


def test_try_llm_enrich_override_rejects_invalid_meaning(monkeypatch, tmp_path):
    import sys
    import types

    class _FakeEnriched:
        def model_dump(self):
            return {
                "tags": "sentence",
                "meaning": "But it just doesn't seem right to me.",
                "de_1": "Aber mir kommt das einfach nicht richtig vor.",
                "en_1": "But it just doesn't seem right to me.",
                "word_inf": "Aber mir kommt das einfach nicht richtig vor.",
            }

    fake_module = types.SimpleNamespace(
        llm_enrich_term=lambda term, meaning_hint=None: _FakeEnriched()
    )
    monkeypatch.setenv("GNW_ENABLE_NW1_LLM_ENRICH", "1")
    monkeypatch.setitem(sys.modules, "gnw_pipeline.nw1_llm_enrich", fake_module)

    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=tmp_path / "out.md",
    )

    assert processor.try_llm_enrich_override(
        term="Aber mir kommt das einfach nicht richtig vor.",
        meaning_hint=None,
    ) is None


def test_try_llm_enrich_override_raises_on_auth_failure(monkeypatch, tmp_path):
    import sys
    import types

    from pydantic_ai.exceptions import ModelHTTPError

    def _raise_auth(*_args, **_kwargs):
        raise ModelHTTPError(
            status_code=401,
            model_name="ds/deepseek-v4-flash",
            body={"message": "Authentication failed"},
        )

    fake_module = types.SimpleNamespace(llm_enrich_term=_raise_auth)
    monkeypatch.setenv("GNW_ENABLE_NW1_LLM_ENRICH", "1")
    monkeypatch.setitem(sys.modules, "gnw_pipeline.nw1_llm_enrich", fake_module)

    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=tmp_path / "out.md",
    )

    try:
        processor.try_llm_enrich_override(
            term="Meeresspiegel",
            meaning_hint="sea level",
        )
    except RuntimeError as exc:
        assert "NW1 LLM authentication failed" in str(exc)
    else:
        raise AssertionError("Expected NW1 auth failures to surface as actionable runtime errors.")
