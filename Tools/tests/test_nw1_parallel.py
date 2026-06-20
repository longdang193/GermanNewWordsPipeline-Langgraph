from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from scripts.process_requirement1 import GermanVocabProcessor


class _FakeCfg:
    def __init__(self, parallelism: int):
        self.nw1 = SimpleNamespace(parallelism=parallelism)


def test_process_parallelizes_independent_terms(monkeypatch, tmp_path: Path) -> None:
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=tmp_path / "out.md",
    )

    monkeypatch.setattr(processor, "extract_word_list", lambda: ["eins", "zwei", "drei"])
    monkeypatch.setattr(processor, "parse_entry", lambda line: (line, None))
    monkeypatch.setattr(processor, "enrich_phrase", lambda word: word)
    monkeypatch.setattr(processor, "detect_pos", lambda word: "other")
    monkeypatch.setattr(processor, "validate_entry_quality", lambda entry: [])
    monkeypatch.setattr(
        "scripts.process_requirement1.load_runtime_config",
        lambda root=None: _FakeCfg(parallelism=3),
    )

    written: dict[str, object] = {}
    monkeypatch.setattr(
        processor,
        "write_entries",
        lambda entries, processed, added, skipped, unresolved: written.update(
            {
                "entries": entries,
                "processed": processed,
                "added": added,
                "skipped": skipped,
                "unresolved": unresolved,
            }
        ),
    )

    def slow_generate(word: str, meaning: str | None, pos: str = "phrase") -> str:
        time.sleep(0.2)
        return f"entry:{word}"

    monkeypatch.setattr(processor, "generate_other_entry", slow_generate)

    start = time.perf_counter()
    processed, added, skipped = processor.process()
    elapsed = time.perf_counter() - start

    assert (processed, added, skipped) == (3, 3, 0)
    assert written["entries"] == ["entry:eins", "entry:zwei", "entry:drei"]
    assert elapsed < 0.45


def test_process_parallel_merge_preserves_input_order(monkeypatch, tmp_path: Path) -> None:
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=tmp_path / "out.md",
    )

    monkeypatch.setattr(processor, "extract_word_list", lambda: ["alpha", "beta", "gamma"])
    monkeypatch.setattr(processor, "parse_entry", lambda line: (line, None))
    monkeypatch.setattr(processor, "enrich_phrase", lambda word: word)
    monkeypatch.setattr(processor, "detect_pos", lambda word: "other")
    monkeypatch.setattr(processor, "validate_entry_quality", lambda entry: [])
    monkeypatch.setattr(
        "scripts.process_requirement1.load_runtime_config",
        lambda root=None: _FakeCfg(parallelism=3),
    )

    written: dict[str, object] = {}
    monkeypatch.setattr(
        processor,
        "write_entries",
        lambda entries, processed, added, skipped, unresolved: written.update({"entries": entries}),
    )

    delays = {"alpha": 0.3, "beta": 0.1, "gamma": 0.2}

    def delayed_generate(word: str, meaning: str | None, pos: str = "phrase") -> str:
        time.sleep(delays[word])
        return f"entry:{word}"

    monkeypatch.setattr(processor, "generate_other_entry", delayed_generate)

    processor.process()

    assert written["entries"] == ["entry:alpha", "entry:beta", "entry:gamma"]
