"""Deterministic text normalization (B-S12.2, B-S12.9).

Normalization here means *making equal things equal*, not making text tidy. Two
copies of the same comment that differ only in Unicode composition or in
invisible characters must hash the same; everything a reader or a classifier
would use to interpret the text must survive untouched.

So this module removes exactly three classes of character — the invisible ones
(zero-width characters used to defeat matching, bidirectional controls, control
codes), the redundant ones (repeated whitespace), and inconsistent line endings —
and changes nothing else. Case is preserved, because shouting is evidence.
Punctuation and emoji are preserved, because they carry tone. Quotation marks are
preserved, because quoted hate and endorsed hate are different labels. Identity
terms are preserved, obviously, and are never a harm signal on their own.

**Nothing here masks, censors, or profanity-filters.** B-S12.9 is explicit:
researchers need the exact wording, and redaction is a display and
report-snapshot concern. A stored string is never softened on its way in.
"""

from __future__ import annotations

import re
import unicodedata

#: Bumped whenever the output of `normalize_text` could change for text that has
#: already been stored. Recorded beside every item, so a re-normalization pass
#: can find the rows produced by an older rule set instead of guessing.
NORMALIZATION_VERSION = "1.0.0"

#: Every invisible character is written as a code point rather than pasted in.
#: A literal zero-width character in source is unreviewable — it looks like
#: nothing — and this module exists precisely to deal with that property.
ZERO_WIDTH_JOINER = chr(0x200D)

#: Characters that change nothing a reader sees but everything a matcher does.
_INVISIBLE = frozenset(
    {
        chr(0x00AD),  # soft hyphen
        chr(0x200B),  # zero-width space
        chr(0x200C),  # zero-width non-joiner
        chr(0x2060),  # word joiner
        chr(0xFEFF),  # zero-width no-break space, also the byte-order mark
        # Bidirectional controls: legitimate in mixed-direction text, and also
        # the classic way to make a string display differently from how it is
        # stored.
        chr(0x202A),
        chr(0x202B),
        chr(0x202C),
        chr(0x202D),
        chr(0x202E),
        chr(0x2066),
        chr(0x2067),
        chr(0x2068),
        chr(0x2069),
    }
)

#: Unicode space separators, folded to an ordinary space so two otherwise
#: identical strings do not hash differently over a non-breaking space.
_UNICODE_SPACES = re.compile(
    "["
    + chr(0x00A0)
    + chr(0x1680)
    + chr(0x2000)
    + "-"
    + chr(0x200A)
    + chr(0x202F)
    + chr(0x205F)
    + chr(0x3000)
    + "]"
)

_HORIZONTAL_RUN = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_SPACE = re.compile(r"[ \t]+\n")

#: Lowest code point of the main emoji planes, used only as a cheap test for
#: "is this character part of an emoji sequence?".
_PICTOGRAPHIC_FLOOR = 0x1F000


def _is_pictographic(character: str) -> bool:
    """Whether a character is emoji-like, for zero-width-joiner handling."""
    return unicodedata.category(character) == "So" or ord(character) >= _PICTOGRAPHIC_FLOOR


def _strip_invisible(value: str) -> str:
    """Drop invisible characters, keeping joiners that are building an emoji.

    A zero-width joiner between two pictographs is what makes a family or a
    profession emoji render as one glyph; removing it would corrupt the text.
    Anywhere else it is noise at best and matcher evasion at worst.
    """
    kept: list[str] = []
    for index, character in enumerate(value):
        if character == ZERO_WIDTH_JOINER:
            previous = value[index - 1] if index > 0 else ""
            following = value[index + 1] if index + 1 < len(value) else ""
            joins_emoji = (
                bool(previous)
                and bool(following)
                and _is_pictographic(previous)
                and _is_pictographic(following)
            )
            if joins_emoji:
                kept.append(character)
            continue
        if character in _INVISIBLE:
            continue
        # Control characters, except the two that give text its structure.
        if unicodedata.category(character) == "Cc" and character not in "\n\t":
            continue
        kept.append(character)
    return "".join(kept)


def normalize_text(value: str | None) -> str | None:
    """Return the canonical form of one piece of source text.

    `None` in, `None` out: an item with no text differs from an item whose text
    is empty, and collapsing the two would turn "not collected" into "collected
    and empty" — exactly the substitution this project must not make.
    """
    if value is None:
        return None

    # NFC rather than NFKC. NFKC folds typographic variants that carry meaning
    # here: it rewrites ligatures, superscripts, and full-width forms, and
    # stylised Unicode is one of the ways hateful text evades matching, so
    # flattening it would destroy evidence of the evasion itself.
    text = unicodedata.normalize("NFC", value)
    text = _strip_invisible(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _UNICODE_SPACES.sub(" ", text)
    text = _HORIZONTAL_RUN.sub(" ", text)
    text = _TRAILING_SPACE.sub("\n", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def truncate_excerpt(value: str | None, limit: int) -> str | None:
    """Cut a permitted excerpt to `limit` characters on a word boundary.

    Excerpt length is a licensing constraint rather than a display preference:
    the reviewed feed terms permit a short excerpt and nothing more.
    """
    if value is None:
        return None
    if len(value) <= limit:
        return value
    window = value[: limit + 1]
    boundary = window.rfind(" ")
    cut = window[:boundary] if boundary > limit // 2 else value[:limit]
    return cut.rstrip() + "…"


def normalize_language(value: str | None) -> str | None:
    """Reduce a language tag to its two-letter subtag, or `None` if unusable.

    `None` means "not determined" and is stored as such. A detector that failed
    must never leave behind a plausible-looking `en`, because the English-only
    MVP gate would then admit text nobody actually checked.
    """
    if value is None:
        return None
    primary = value.strip().lower().replace("_", "-").split("-")[0]
    return primary if len(primary) == 2 and primary.isalpha() else None
