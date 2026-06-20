from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_requirement4 import _derive_noun_forms, process_markdown_file


def test_process_requirement4_keeps_tags_last_when_backfilled(tmp_path: Path) -> None:
    input_path = tmp_path / "in.md"
    output_path = tmp_path / "out.md"
    input_path.write_text(
        "\n".join(
            [
                "SSTART",
                "%VOCAB (German) ver 3",
                "word: Aber mir kommt das einfach nicht richtig vor.",
                "meaning: Aber mir kommt das einfach nicht richtig vor. = Das drückt aus, dass etwas nicht korrekt oder angemessen erscheint / But it just doesn't seem right to me.",
                "de_1: Aber mir kommt das einfach nicht richtig vor.",
                "en_1: But it just doesn't seem right to me.",
                "word_inf: Aber mir kommt das einfach nicht richtig vor.",
                "see_also:",
                "[richtig|nid1] = correct",
                "Tags:",
                "EEND",
                "",
            ]
        ),
        encoding="utf-8",
    )

    process_markdown_file(
        input_path,
        output_path,
        {
            "aber mir kommt das einfach nicht richtig vor.": {
                "Tags": "sentence",
            }
        },
    )

    out = output_path.read_text(encoding="utf-8")
    assert "see_also:\n[richtig|nid1] = correct\nTags: sentence\nEEND" in out


def test_derive_noun_forms_handles_compound_umlaut_plural() -> None:
    assert _derive_noun_forms(
        "der Sicherheitsabstand",
        "des Sicherheitsabstands",
        "Sicherheitsabstände",
    ) == "-s, ⸚e"
