from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "Tools" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_see_also_authenticity as authenticity


def test_extract_word_reuses_nw3_percent_word_parser() -> None:
    block_lines = [
        "SSTART",
        "%word: Feigling",
        "see_also:",
        "die [Angst|nid1718783284420] = fear, anxiety",
        "[ängstlich|nid1718783284421] = anxious",
        "EEND",
    ]

    assert authenticity.extract_word(block_lines) == "Feigling"
