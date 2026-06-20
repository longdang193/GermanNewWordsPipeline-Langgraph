from __future__ import annotations

import json

from scripts.process_requirement1 import GermanVocabProcessor
from scripts.validate_word_list import extract_unresolved_words


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
