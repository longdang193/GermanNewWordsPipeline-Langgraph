from __future__ import annotations

import sys
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "Tools"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scripts.process_requirement1 as process_requirement1
from scripts.process_requirement1 import GermanVocabProcessor
from mdproc.validation_core import iter_blocks


def test_resolve_entry_candidate_returns_reason_code_for_missing_meaning(tmp_path: Path) -> None:
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=tmp_path / "out.md",
    )
    processor.try_llm_enrich_override = lambda **_kwargs: None  # type: ignore[method-assign]

    status, payload = processor._resolve_entry_candidate("Absprache", None)

    assert status == "unresolved"
    assert payload["term"] == "Absprache"
    assert payload["reason_code"] == "missing_meaning"


def test_process_fails_and_does_not_write_canonical_output_when_unresolved(monkeypatch, tmp_path: Path) -> None:
    output_file = tmp_path / "out.md"
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=output_file,
    )
    monkeypatch.setattr(processor, "try_llm_enrich_override", lambda **_kwargs: None)

    monkeypatch.setattr(processor, "extract_word_list", lambda: ["Absprache"])
    monkeypatch.setattr(processor, "parse_entry", lambda line: (line, None))
    monkeypatch.setattr(processor, "enrich_phrase", lambda word: word)

    with pytest.raises(RuntimeError) as exc:
        processor.process()

    assert "missing_meaning" in str(exc.value)
    assert not output_file.exists()


def test_try_llm_enrich_override_does_not_retry_auth_failure(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    processor = GermanVocabProcessor(requirement_file='x', output_file='y')  # type: ignore[arg-type]
    monkeypatch.setattr(
        process_requirement1,
        'load_runtime_config',
        lambda **_kwargs: type('Cfg', (), {'nw1': type('Nw1', (), {'enable_llm_enrich': True, 'llm_repair_max_attempts': 3, 'llm_repair_print_trace': True})()})(),
    )

    class AuthBoom(Exception):
        pass

    def fake_enrich_term(*, term: str, meaning_hint: str | None):
        raise AuthBoom('bad auth')

    class FakeRuntime:
        @staticmethod
        def classify_openai_compatible_error(exc: BaseException) -> str | None:
            return 'auth'

    module = type('FakeModule', (), {'llm_enrich_term': staticmethod(fake_enrich_term)})
    monkeypatch.setitem(sys.modules, 'gnw_pipeline.llm_runtime', FakeRuntime)
    monkeypatch.setitem(sys.modules, 'gnw_pipeline.nw1_llm_enrich', module)

    with pytest.raises(RuntimeError) as exc:
        processor.try_llm_enrich_override(term='das soziale Verhalten', meaning_hint=None)

    out = capsys.readouterr().out
    assert 'NW1 repair: trying LLM enrich' in out
    assert 'NW1 repair retry' not in out
    assert 'authentication failed' in str(exc.value).lower()


def test_try_llm_enrich_override_retries_transient_failure_then_succeeds(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    processor = GermanVocabProcessor(requirement_file='x', output_file='y')  # type: ignore[arg-type]
    monkeypatch.setattr(
        process_requirement1,
        'load_runtime_config',
        lambda **_kwargs: type('Cfg', (), {'nw1': type('Nw1', (), {'enable_llm_enrich': True, 'llm_repair_max_attempts': 3, 'llm_repair_print_trace': True})()})(),
    )

    calls = {'count': 0}

    class FakeEnriched:
        def model_dump(self):
            return {
                'tags': 'noun',
                'meaning': 'das soziale Verhalten = Art, wie Menschen miteinander umgehen / social behavior',
                'de_1': 'Das soziale Verhalten ist im Team wichtig.',
                'en_1': 'Social behavior is important in the team.',
                'word_inf': 'das soziale Verhalten',
                'noun_gender': 'das',
                'noun_genetiv': 'des sozialen Verhaltens',
                'noun_plural': '-',
                'noun_forms': '-, -',
                'verb_present': None,
                'verb_past': None,
                'verb_perfect': None,
            }

    def fake_enrich_term(*, term: str, meaning_hint: str | None):
        calls['count'] += 1
        if calls['count'] == 1:
            raise RuntimeError('temporary upstream failure')
        return FakeEnriched()

    class FakeRuntime:
        @staticmethod
        def classify_openai_compatible_error(exc: BaseException) -> str | None:
            return None

    module = type('FakeModule', (), {'llm_enrich_term': staticmethod(fake_enrich_term)})
    monkeypatch.setitem(sys.modules, 'gnw_pipeline.llm_runtime', FakeRuntime)
    monkeypatch.setitem(sys.modules, 'gnw_pipeline.nw1_llm_enrich', module)
    monkeypatch.setattr(processor, 'validate_entry_quality', lambda _entry: [])

    result = processor.try_llm_enrich_override(term='das soziale Verhalten', meaning_hint=None)

    out = capsys.readouterr().out
    assert result is not None
    assert calls['count'] == 2
    assert 'NW1 repair retry 1/3' in out
    assert 'NW1 repair succeeded' in out


def test_try_llm_enrich_override_stops_early_on_repeated_deterministic_quality_issue(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    processor = GermanVocabProcessor(requirement_file='x', output_file='y')  # type: ignore[arg-type]
    monkeypatch.setattr(
        process_requirement1,
        'load_runtime_config',
        lambda **_kwargs: type('Cfg', (), {'nw1': type('Nw1', (), {'enable_llm_enrich': True, 'llm_repair_max_attempts': 4, 'llm_repair_print_trace': True})()})(),
    )

    calls = {'count': 0}

    class FakeEnriched:
        def model_dump(self):
            return {
                'tags': 'noun',
                'meaning': 'das soziale Verhalten = Art, wie Menschen miteinander umgehen / social behavior',
                'de_1': 'Das soziale Verhalten ist im Team wichtig.',
                'en_1': 'Social behavior is important in the team.',
                'word_inf': 'das soziale Verhalten',
                'noun_gender': 'das',
                'noun_genetiv': 'des sozialen Verhaltens',
                'noun_plural': '-',
                'noun_forms': '-, -',
                'verb_present': None,
                'verb_past': None,
                'verb_perfect': None,
            }

    def fake_enrich_term(*, term: str, meaning_hint: str | None):
        calls['count'] += 1
        return FakeEnriched()

    class FakeRuntime:
        @staticmethod
        def classify_openai_compatible_error(exc: BaseException) -> str | None:
            return None

    module = type('FakeModule', (), {'llm_enrich_term': staticmethod(fake_enrich_term)})
    monkeypatch.setitem(sys.modules, 'gnw_pipeline.llm_runtime', FakeRuntime)
    monkeypatch.setitem(sys.modules, 'gnw_pipeline.nw1_llm_enrich', module)
    monkeypatch.setattr(processor, 'validate_entry_quality', lambda _entry: ['same deterministic issue'])

    result = processor.try_llm_enrich_override(term='das soziale Verhalten', meaning_hint=None)

    out = capsys.readouterr().out
    assert result is None
    assert calls['count'] == 2
    assert 'NW1 repair retry 1/4' in out
    assert 'NW1 repair retry 2/4' in out
    assert 'NW1 repair failed' in out


@pytest.mark.parametrize(
    ("word", "de_1", "expected_fragment"),
    [
        ("ich würde nicht wollen, dass …", "Ich möchte nicht, dass …", "missing_terminal_punctuation"),
        ("in der Kinderkrippe sein", "in der Kinderkrippe sein", "missing_terminal_punctuation"),
        ("mitunter", "mitunter", "missing_terminal_punctuation"),
    ],
)
def test_validate_entry_quality_rejects_invalid_de1_generation_time(
    tmp_path: Path,
    word: str,
    de_1: str,
    expected_fragment: str,
) -> None:
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / 'req.md',
        output_file=tmp_path / 'out.md',
    )

    entry = f"""SSTART
%VOCAB (German) ver 3
word: {word}
meaning: {word} = einfache Bedeutung / simple meaning
de_1: {de_1}
en_1: placeholder translation
word_inf: {word}
Tags: phrase
EEND"""

    issues = processor.validate_entry_quality(entry)

    assert any(expected_fragment in issue for issue in issues)


def test_validate_entry_quality_accepts_valid_realized_sentence(tmp_path: Path) -> None:
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / 'req.md',
        output_file=tmp_path / 'out.md',
    )

    entry = """SSTART
%VOCAB (German) ver 3
word: eine warme Umgebung
meaning: eine warme Umgebung = ein angenehmer, warmer Ort / a warm environment
de_1: Kinder brauchen eine warme Umgebung.
en_1: Children need a warm environment.
word_inf: eine warme Umgebung
Tags: phrase
EEND"""

    issues = processor.validate_entry_quality(entry)

    assert issues == []


def test_process_writes_clean_and_review_tail_before_raising_on_fatal_unresolved(
    monkeypatch,
    tmp_path: Path,
) -> None:
    output_file = tmp_path / "out.md"
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=output_file,
    )

    clean_entry = """SSTART
%VOCAB (German) ver 3
word: Alpha
meaning: Alpha = erste Sache / first thing
de_1: Alpha ist heute wichtig.
en_1: Alpha is important today.
word_inf: Alpha
Tags: noun
EEND"""
    tail_entry = """SSTART
%VOCAB (German) ver 3
word: Beta
meaning: Beta = zweite Sache / second thing
de_1: Beta heute.
en_1: Beta today.
word_inf: Beta
Tags: noun
EEND"""

    def fake_resolve(word: str, _meaning: str | None):
        if word == "Alpha":
            return ("entry", clean_entry)
        if word == "Beta":
            return ("entry", tail_entry)
        return ("unresolved", {
            "term": word,
            "reason_code": "missing_meaning",
            "origin_reason_code": "missing_meaning",
            "final_blocker_code": "target_not_realized",
            "final_blocker_codes": ["target_not_realized"],
            "detail": "Missing LLM-authored meaning.",
        })

    monkeypatch.setattr(processor, "extract_word_list", lambda: ["Alpha", "Beta", "Gamma"])
    monkeypatch.setattr(processor, "parse_entry", lambda line: (line, None))
    monkeypatch.setattr(processor, "enrich_phrase", lambda word: word)
    monkeypatch.setattr(processor, "_resolve_entry_candidate", fake_resolve)
    monkeypatch.setattr(
        processor,
        "validate_entry_quality",
        lambda entry: [] if "word: Alpha" in entry else ["target_not_realized: de_1 does not realize target lexeme."],
    )

    with pytest.raises(RuntimeError) as exc:
        processor.process()

    assert "missing_meaning" in str(exc.value)
    assert output_file.exists()

    text = output_file.read_text(encoding="utf-8")
    assert "## UNRESOLVED PART" in text
    assert text.index("word: Alpha") < text.index("## UNRESOLVED PART") < text.index("word: Beta")

    blocks = list(iter_blocks(text.splitlines()))
    assert len(blocks) == 2
    assert "word: Alpha" in "\n".join(blocks[0].body_lines)
    assert "word: Beta" in "\n".join(blocks[1].body_lines)

    assert "REVIEW_TAIL_JSON" not in text
    assert "UNRESOLVED_JSON" not in text


def test_process_succeeds_when_only_review_tail_exists(monkeypatch, tmp_path: Path) -> None:
    output_file = tmp_path / "out.md"
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=output_file,
    )

    tail_entry = """SSTART
%VOCAB (German) ver 3
word: Beta
meaning: Beta = zweite Sache / second thing
de_1: Beta heute.
en_1: Beta today.
word_inf: Beta
Tags: noun
EEND"""

    monkeypatch.setattr(processor, "extract_word_list", lambda: ["Beta"])
    monkeypatch.setattr(processor, "parse_entry", lambda line: (line, None))
    monkeypatch.setattr(processor, "enrich_phrase", lambda word: word)
    monkeypatch.setattr(processor, "_resolve_entry_candidate", lambda *_args: ("entry", tail_entry))
    monkeypatch.setattr(processor, "validate_entry_quality", lambda _entry: ["target_not_realized: de_1 does not realize target lexeme."])

    processed, added, skipped = processor.process()

    assert (processed, added, skipped) == (1, 1, 0)
    text = output_file.read_text(encoding="utf-8")
    assert "## UNRESOLVED PART" in text
    assert len(list(iter_blocks(text.splitlines()))) == 1


def test_failed_repair_last_valid_block_routes_to_unresolved_part(monkeypatch, tmp_path: Path) -> None:
    output_file = tmp_path / "out.md"
    processor = GermanVocabProcessor(
        requirement_file=tmp_path / "req.md",
        output_file=output_file,
    )

    remembered_block = """SSTART
%VOCAB (German) ver 3
word: Gamma
meaning: Gamma = dritte Sache / third thing
de_1: Gamma heute.
en_1: Gamma today.
word_inf: Gamma
Tags: noun
EEND"""

    def fake_try_llm_enrich_override(*, term: str, meaning_hint: str | None):
        processor._last_llm_repair_issues[term] = "target_not_realized: de_1 does not realize target lexeme."
        if term == "Gamma":
            processor._last_llm_repair_entries[term] = remembered_block
        return None

    monkeypatch.setattr(processor, "try_llm_enrich_override", fake_try_llm_enrich_override)
    monkeypatch.setattr(processor, "extract_word_list", lambda: ["Gamma", "Delta"])
    monkeypatch.setattr(processor, "parse_entry", lambda line: (line, None))
    monkeypatch.setattr(processor, "enrich_phrase", lambda word: word)

    def fake_generate_other_entry(word: str, meaning: str | None):
        raise ValueError(f"Missing LLM-authored meaning for '{word}'. Add override data instead of using code-generated fallback.")

    monkeypatch.setattr(processor, "generate_other_entry", fake_generate_other_entry)
    monkeypatch.setattr(
        processor,
        "detect_pos",
        lambda _word: "other",
    )
    monkeypatch.setattr(
        processor,
        "validate_entry_quality",
        lambda entry: ["target_not_realized: de_1 does not realize target lexeme."] if "word: Gamma" in entry else [],
    )

    with pytest.raises(RuntimeError) as exc:
        processor.process()

    assert "missing_meaning" in str(exc.value)
    text = output_file.read_text(encoding="utf-8")
    assert "## UNRESOLVED PART" in text
    assert "word: Gamma" in text

