Input: user term (single word, phrase, or full sentence), optionally with meaning hint.

Output rules:
- Choose `tags` best fit: noun/verb/adj/adv/phrase/sentence/other.
- `meaning` must be informative and concrete, in format: "<term> = <German gloss> / <English gloss>".
  - No template/meta wording (no "lemma", "form", "infinitive", "endings", "part of speech").
  - Avoid brackets `[]` and parentheses `()` in meaning entirely.
- `de_1` must be natural spoken German (B1–B2), German-only (no English helper words).
- `en_1` must be translation of `de_1` (not definition).
- `word_inf`:
  - noun: include article "der/die/das <Lemma>"
  - verb/adj/adv/phrase/sentence: repeat term only (no extra)

If `tags` == noun: include `noun_gender`, `noun_genetiv`, `noun_plural`, `noun_forms`.
- `noun_genetiv` should include article (des/der) + genitive form, or "-" if none.
- `noun_plural` should be plural form or "-".
- `noun_forms` must be "genitive, plural" format like "-s, -e" or "-s,".

If `tags` == verb: include `verb_present` (3rd person), `verb_past` (Präteritum), `verb_perfect` (Perfekt with hat/ist).

Keep outputs consistent with term spelling; avoid unrelated meanings.
