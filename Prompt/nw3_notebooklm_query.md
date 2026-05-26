For each item in list below, return ONLY Markdown blocks in this exact format (real newlines):

SSTART
%word: <item>
see_also:
[related_word|nid<digits>] = <short meaning>
[related_word|nid<digits>] = <short meaning>
[related_word|nid<digits>] = <short meaning>
(Provide 3 to 5 see_also entries; prefer 3 if unsure.)
EEND

Rules:
- Use existing nids from this notebook.
- Never say 'not found' or mention missing sources; always provide best matches.
- For nouns: include der/die/das before [Noun|nid...].
- One see_also entry per line.
- No extra commentary outside SSTART...EEND blocks.

List:
{word_list}
