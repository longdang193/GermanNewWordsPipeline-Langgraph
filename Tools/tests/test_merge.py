from __future__ import annotations
import textwrap
from mdproc.core import merge_see_also, preprocess_file1, process_markdown


def dd(s: str) -> str:
    return textwrap.dedent(s).lstrip("\n").rstrip() + "\n"


def test_preprocess_dedup_by_word_and_whitespace():
    file1 = dd(
        """
    SSTART
    word: A
    see_also:
    one
    EEND

    SSTART
    word: A
    see_also:
    two
    EEND

    SSTART
    word: B
    see_also:
    three  
    EEND
    """
    )
    cleaned = preprocess_file1(file1)
    # keeps first A, drops second A; keeps B
    assert cleaned.count("word: A") == 1
    assert cleaned.count("word: B") == 1
    # trailing spaces removed
    for line in cleaned.splitlines():
        assert not line.endswith("  ")
    # ensure single spaces inside lines (rough smoke check)
    assert "three  " not in cleaned


def test_merge_inserts_above_tags_and_dedups():
    file1 = dd(
        """
    SSTART
    word: Bauarbeiten
    see_also:
    X
    Y
    X
    EEND
    """
    )
    file2 = dd(
        """
    Preamble

    SSTART
    word: Bauarbeiten
    meaning: something
    see_also:
    Bauarbeiten
    Tags: noun
    EEND

    Epilogue
    """
    )
    merged = merge_see_also(file1, file2)
    # placement: above Tags
    assert "see_also:\nBauarbeiten\nX\nY\nTags: noun" in merged
    # dedup preserved first occurrence; only one X
    assert merged.count("\nX\n") == 1


def test_merge_inserts_above_end_when_no_tags():
    file1 = dd(
        """
    SSTART
    word: W
    see_also:
    a
    b
    EEND
    """
    )
    file2 = dd(
        """
    SSTART
    word: W
    meaning: m
    EEND
    """
    )
    merged = merge_see_also(file1, file2)
    # see_also goes just above EEND
    assert "meaning: m\nsee_also:\na\nb\nEEND" in merged


def test_merge_leaves_unmatched_blocks_unchanged():
    file1 = dd(
        """
    SSTART
    WORD: OnlyHere
    see_also:
    a
    EEND
    """
    )
    file2 = dd(
        """
    SSTART
    WORD: Different
    EEND
    """
    )
    merged = merge_see_also(file1, file2)
    # File 2 untouched
    assert merged.strip() == file2.strip()


def test_merge_ignores_file1_blocks_without_see_also():
    file1 = dd(
        """
    SSTART
    WORD: Z
    EEND
    """
    )
    file2 = dd(
        """
    SSTART
    WORD: Z
    Tags: noun
    EEND
    """
    )
    merged = merge_see_also(file1, file2)
    # no new see_also added
    assert "see_also:" not in merged


def test_process_markdown_preserves_sentence_tag():
    src = dd(
        """
    SSTART
    word: Aber mir kommt das einfach nicht richtig vor.
    Tags: sentence
    EEND
    """
    )

    out = process_markdown(src)

    assert "Tags: sentence" in out
