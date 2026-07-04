from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "Tools"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scripts.validate_word_list as validate_word_list
from scripts.process_requirement1 import GermanVocabProcessor
from scripts.validate_word_list import extract_unresolved_words, validate_noun_block_shape
from mdproc.validation_core import validate_word_field_rules


def test_extract_unresolved_words_prefers_json_payload_with_commas() -> None:
    lines = [
        '<!-- UNRESOLVED_JSON: ["Sicherheitsabstand", "Es heißt, es macht einen verrückt"] -->'
    ]

    assert extract_unresolved_words(lines) == [
        "Sicherheitsabstand",
        "Es heißt, es macht einen verrückt",
    ]


def test_write_entries_serializes_unresolved_as_json_comment(tmp_path) -> None:
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=tmp_path / "out.md",
    )

    processor.write_entries(
        entries=[],
        processed=2,
        added=0,
        skipped=0,
        unresolved=["Sicherheitsabstand", "Es heißt, es macht einen verrückt"],
    )

    text = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "<!-- UNRESOLVED_JSON: " in text

    payload = text.split("<!-- UNRESOLVED_JSON: ", 1)[1].split(" -->", 1)[0]
    assert json.loads(payload) == [
        "Sicherheitsabstand",
        "Es heißt, es macht einen verrückt",
    ]

def test_main_fails_when_unresolved_entries_are_present(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts_dir = repo / "Tools" / "scripts"
    scripts_dir.mkdir(parents=True)
    requirement = repo / "Requirement" / "Requirement NW1 - German new words prompt.md"
    requirement.parent.mkdir(parents=True)
    requirement.write_text("unused", encoding="utf-8")
    vocab = repo / "Outputs" / "01_words.md"
    vocab.parent.mkdir(parents=True)
    vocab.write_text(
        "SSTART\n%VOCAB (German) ver 3\nword: A\nmeaning: A = aa / aa\nde_1: A.\nen_1: A.\nTags: noun\nEEND\n"
        '<!-- UNRESOLVED_JSON: ["B"] -->\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(validate_word_list, "__file__", str(scripts_dir / "validate_word_list.py"))
    monkeypatch.setattr(validate_word_list, "extract_word_list", lambda *_args, **_kwargs: (["A", "B"], "fixture"))
    monkeypatch.setattr(validate_word_list, "analyze_block_structure", lambda *_args, **_kwargs: (1, []))
    monkeypatch.setattr(validate_word_list, "validate_no_template_placeholders", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_word_field_rules", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_meaning_field_rules", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_no_generic_content", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_required_core_fields", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_tags_last", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_no_blank_lines_between_fields", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_unique_fields_per_block", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(validate_word_list, "validate_noun_block_shape", lambda *_args, **_kwargs: [])

    assert validate_word_list.main() == 1

def test_validate_noun_block_shape_allows_regular_masculine_noun_ending_en() -> None:
    lines = [
        'SSTART',
        '%VOCAB (German) ver 3',
        'word: Fahrstreifen',
        'meaning: der Fahrstreifen = ein Streifen auf der Straße für ein Fahrzeug / lane',
        'de_1: Wir fuhren auf dem rechten Fahrstreifen.',
        'en_1: We drove in the right lane.',
        'word_inf: der Fahrstreifen',
        'noun_gender: der',
        'noun_genetiv: des Fahrstreifens',
        'noun_plural: Fahrstreifen',
        'noun_forms: -s, -',
        'Tags: noun',
        'EEND',
    ]

    assert validate_noun_block_shape(lines) == []

def test_override_for_einheimische_uses_plural_noun() -> None:
    processor = GermanVocabProcessor(requirement_file='dummy', output_file='dummy')  # type: ignore[arg-type]

    override = processor.get_override('Einheimische')

    assert override is not None
    assert override['word_inf'] == 'die Einheimischen'
    assert override['noun_gender'] == 'die (plural)'

def test_generate_noun_entry_preserves_input_word_with_article() -> None:
    processor = GermanVocabProcessor(requirement_file='dummy', output_file='dummy')  # type: ignore[arg-type]

    entry = processor.generate_noun_entry('das soziale Verhalten', 'Art, wie Menschen miteinander umgehen / social behavior')

    assert 'word: das soziale Verhalten' in entry
    assert 'word_inf: das soziale Verhalten' in entry

def test_build_override_entry_preserves_input_word_with_article() -> None:
    processor = GermanVocabProcessor(requirement_file='dummy', output_file='dummy')  # type: ignore[arg-type]

    entry = processor.build_override_entry(
        'Die Elbe',
        {
            'tags': 'noun',
            'meaning': 'die Elbe = großer Fluss in Mitteleuropa / major river in Central Europe',
            'de_1': 'Die Elbe fließt durch Hamburg.',
            'en_1': 'The Elbe flows through Hamburg.',
            'word_inf': 'die Elbe',
            'noun_gender': 'die',
            'noun_genetiv': 'der Elbe',
            'noun_plural': '-',
            'noun_forms': '-',
        },
    )

    assert 'word: Die Elbe' in entry
    assert 'word_inf: die Elbe' in entry


def test_validate_noun_block_shape_allows_article_led_source_noun_phrase() -> None:
    lines = [
        'SSTART',
        '%VOCAB (German) ver 3',
        'word: das soziale Verhalten',
        'meaning: das soziale Verhalten = Art, wie Menschen miteinander umgehen / social behavior',
        'de_1: Das soziale Verhalten ist im Team wichtig.',
        'en_1: Social behavior is important in the team.',
        'word_inf: das soziale Verhalten',
        'noun_gender: das',
        'noun_genetiv: des sozialen Verhaltens',
        'noun_plural: -',
        'noun_forms: -, -',
        'Tags: noun',
        'EEND',
    ]

    assert validate_noun_block_shape(lines) == []


def test_validate_noun_block_shape_allows_article_casefold_match() -> None:
    lines = [
        'SSTART',
        '%VOCAB (German) ver 3',
        'word: Die Elbe',
        'meaning: die Elbe = großer Fluss in Mitteleuropa / major river in Central Europe',
        'de_1: Die Elbe fließt durch Hamburg.',
        'en_1: The Elbe flows through Hamburg.',
        'word_inf: die Elbe',
        'noun_gender: die',
        'noun_genetiv: der Elbe',
        'noun_plural: -',
        'noun_forms: -',
        'Tags: noun',
        'EEND',
    ]

    assert validate_noun_block_shape(lines) == []


def test_validate_word_field_rules_allows_article_led_source_noun_identity() -> None:
    lines = [
        'SSTART',
        '%VOCAB (German) ver 3',
        'word: das soziale Verhalten',
        'meaning: das soziale Verhalten = Art, wie Menschen miteinander umgehen / social behavior',
        'de_1: Das soziale Verhalten ist im Team wichtig.',
        'en_1: Social behavior is important in the team.',
        'word_inf: das soziale Verhalten',
        'noun_gender: das',
        'noun_genetiv: des sozialen Verhaltens',
        'noun_plural: -',
        'noun_forms: -, -',
        'Tags: noun',
        'EEND',
    ]

    assert validate_word_field_rules(lines) == []
