from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


NounGender = Literal["der", "die", "das", "die (plural)", "der/die", "die/das"]


class SeeAlsoRef(BaseModel):
    gender: Literal["der", "die", "das"] | None = None
    related_word: str
    nid: str
    meaning_en: str

    @field_validator("nid")
    @classmethod
    def _nid_digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("nid must be digits only")
        return v

    @field_validator("related_word", "meaning_en")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        vv = v.strip()
        if not vv:
            raise ValueError("must be non-empty")
        return vv


class VocabEntry(BaseModel):
    word: str
    meaning: str
    de_1: str
    en_1: str
    word_inf: str
    tags: list[str] = Field(default_factory=list)

    noun_gender: NounGender | None = None
    noun_genetiv: str | None = None
    noun_plural: str | None = None
    noun_forms: str | None = None

    verb_present: str | None = None
    verb_past: str | None = None
    verb_perfect: str | None = None

    see_also: list[SeeAlsoRef] = Field(default_factory=list)

    @field_validator("word")
    @classmethod
    def _word_hygiene(cls, v: str) -> str:
        vv = v.strip()
        if not vv:
            raise ValueError("word must be non-empty")
        if "(" in vv or ")" in vv:
            raise ValueError("word must not include parenthetical gloss")
        return vv

    @field_validator("meaning", "de_1", "en_1", "word_inf")
    @classmethod
    def _text_non_empty(cls, v: str) -> str:
        vv = v.strip()
        if not vv:
            raise ValueError("must be non-empty")
        return vv

    @model_validator(mode="after")
    def _pos_consistency(self) -> "VocabEntry":
        is_noun = self.noun_gender is not None
        is_verb = any(v is not None for v in (self.verb_present, self.verb_past, self.verb_perfect))

        if is_noun and is_verb:
            raise ValueError("entry cannot be noun and verb simultaneously")

        if is_noun:
            lowered = self.word.casefold()
            if lowered.startswith(("der ", "die ", "das ")):
                raise ValueError("noun word must not start with article; use word_inf")
            if self.noun_forms is None or not self.noun_forms.strip():
                raise ValueError("noun must have noun_forms")

        return self


class FinalVocabDatabase(BaseModel):
    entries: list[VocabEntry]
    unresolved: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

