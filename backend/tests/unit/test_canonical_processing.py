"""Normalization, URLs, hashing, context, and encryption (B-S12.7, B-S12.9).

The theme running through these is that normalization must make *equal things
equal* without changing what anything means. Two copies of the same comment have
to hash alike; a quotation, an emoji, a slur, and a shout all have to survive
byte for byte.
"""

from __future__ import annotations

import base64

import pytest

from amanah.canonical.context import CONTEXT_FIELD_LIMITS, assemble_context
from amanah.canonical.encryption import (
    KEY_LENGTH_BYTES,
    ContentCipher,
    ContentEncryptionError,
    build_cipher,
)
from amanah.canonical.hashing import content_hash, datapack_source_item_id, headline_key
from amanah.canonical.text import (
    ZERO_WIDTH_JOINER,
    normalize_language,
    normalize_text,
    truncate_excerpt,
)
from amanah.canonical.urls import (
    UrlNormalizationError,
    canonical_url_key,
    normalize_url,
    safe_url,
)
from amanah.ingestion.contract import ContentContext

# -- text -----------------------------------------------------------------


def test_absent_text_stays_absent() -> None:
    """`None` and `""` mean different things and must not be collapsed."""
    assert normalize_text(None) is None
    assert normalize_text("   ") == ""


def test_unicode_composition_is_made_consistent() -> None:
    """The same word typed two ways must hash the same.

    Written as code points because the two forms are visually identical: a
    reader cannot check a test whose two inputs look the same on the page.
    """
    composed = "caf" + chr(0x00E9)
    decomposed = "cafe" + chr(0x0301)

    assert composed != decomposed
    assert normalize_text(composed) == normalize_text(decomposed)


def test_stylised_unicode_is_preserved_rather_than_flattened() -> None:
    """Mathematical sans-serif letters that read as "APAF".

    NFKC would fold them to plain ASCII. Stylised Unicode is one of the ways
    hateful text evades matching, so flattening it would destroy evidence of
    the evasion itself.
    """
    stylised = chr(0x1D5A0) + chr(0x1D5AF) + chr(0x1D5A0) + chr(0x1D5A5)

    assert normalize_text(stylised) == stylised


def test_invisible_characters_used_to_defeat_matching_are_removed() -> None:
    zero_width_space = chr(0x200B)
    soft_hyphen = chr(0x00AD)

    assert normalize_text(f"mus{zero_width_space}lim") == "muslim"
    assert normalize_text(f"mus{soft_hyphen}lim") == "muslim"


def test_a_bidirectional_override_is_removed() -> None:
    """A string that displays differently from how it is stored is evasion."""
    override = chr(0x202E)

    assert normalize_text(f"report{override}ed") == "reported"


def test_a_joiner_inside_an_emoji_sequence_is_kept() -> None:
    """Removing it would corrupt the glyph rather than reveal anything."""
    family = f"👨{ZERO_WIDTH_JOINER}👩"

    assert normalize_text(family) == family


def test_punctuation_emoji_and_case_all_survive() -> None:
    """Shouting is evidence, tone is evidence, and neither is ours to tidy."""
    original = "THIS IS NOT OK!! 😡 — see the thread."

    assert normalize_text(original) == original


def test_quotation_marks_survive_normalization() -> None:
    """B-S12.7. Quoted hate and endorsed hate are different labels, and the
    quotation marks are how a classifier tells them apart."""
    counterspeech = 'Someone said "they do not belong here" and that is the problem.'

    assert normalize_text(counterspeech) == counterspeech


def test_stored_text_is_never_censored() -> None:
    """B-S12.9. Researchers need the exact wording; redaction is a display
    concern. Nothing in normalization may mask a character."""
    blunt = "You damned fools."

    assert normalize_text(blunt) == blunt
    assert "*" not in (normalize_text(blunt) or "")


def test_whitespace_is_collapsed_without_losing_paragraphs() -> None:
    messy = "First   line\r\n\r\n\r\n\r\nSecond line   "

    assert normalize_text(messy) == "First line\n\nSecond line"


def test_normalization_is_idempotent() -> None:
    """A second pass over stored text must not change it again."""
    once = normalize_text("cafe" + chr(0x0301) + chr(0x200B) + "  \r\n test")
    assert once is not None

    assert normalize_text(once) == once


def test_an_excerpt_is_cut_on_a_word_boundary() -> None:
    long_text = "word " * 200

    excerpt = truncate_excerpt(long_text, 40)

    assert excerpt is not None
    assert len(excerpt) <= 41
    assert excerpt.endswith("…")


def test_a_short_excerpt_is_returned_unchanged() -> None:
    assert truncate_excerpt("short", 400) == "short"


def test_an_undetermined_language_stays_null() -> None:
    """A failed detector must not leave behind a plausible-looking `en`."""
    assert normalize_language(None) is None
    assert normalize_language("") is None
    assert normalize_language("und") is None
    assert normalize_language("en-GB") == "en"
    assert normalize_language("FR") == "fr"


# -- URLs -----------------------------------------------------------------


def test_tracking_parameters_are_removed_but_real_ones_are_kept() -> None:
    url = normalize_url("https://example.test/story?utm_source=x&id=42&fbclid=abc")

    assert url == "https://example.test/story?id=42"


def test_a_fragment_never_reaches_storage() -> None:
    assert normalize_url("https://example.test/story#section") == "https://example.test/story"


def test_credentials_in_a_url_are_refused() -> None:
    with pytest.raises(UrlNormalizationError):
        normalize_url("https://user:secret@example.test/story")


@pytest.mark.parametrize(
    "candidate",
    ["ftp://example.test/x", "javascript:alert(1)", "file:///etc/passwd", "data:text/html,x"],
)
def test_only_http_and_https_are_accepted(candidate: str) -> None:
    with pytest.raises(UrlNormalizationError):
        normalize_url(candidate)


def test_the_dedupe_key_folds_the_spellings_of_one_article() -> None:
    """B-S9.4. The same story from two feeds must resolve to one row."""
    spellings = [
        "https://www.example.test/story/",
        "http://example.test/story",
        "https://example.test/story?utm_campaign=newsletter",
    ]

    keys = {canonical_url_key(url) for url in spellings}

    assert len(keys) == 1


def test_the_dedupe_key_keeps_different_articles_apart() -> None:
    assert canonical_url_key("https://example.test/a") != canonical_url_key(
        "https://example.test/b"
    )


def test_an_unusable_url_becomes_none_where_that_is_a_valid_outcome() -> None:
    assert safe_url(None) is None
    assert safe_url("not a url") is None


# -- hashing --------------------------------------------------------------


def test_the_content_hash_is_stable_across_runs() -> None:
    def digest() -> str:
        return content_hash(
            source_key="fixtures",
            content_kind="social_comment",
            normalized_text="Same text.",
            title=None,
            canonical_url=None,
        )

    assert digest() == digest()


def test_the_content_hash_separates_its_fields() -> None:
    """Concatenation without a separator would let `("ab","c")` collide with
    `("a","bc")`."""
    first = content_hash(
        source_key="ab", content_kind="c", normalized_text=None, title=None, canonical_url=None
    )
    second = content_hash(
        source_key="a", content_kind="bc", normalized_text=None, title=None, canonical_url=None
    )

    assert first != second


def test_two_articles_with_only_a_headline_still_hash_apart() -> None:
    """News often has no stored body, so a digest over text alone would make
    every article identical."""
    first = content_hash(
        source_key="rss",
        content_kind="news_article",
        normalized_text=None,
        title="Council debates funding",
        canonical_url="https://example.test/a",
    )
    second = content_hash(
        source_key="rss",
        content_kind="news_article",
        normalized_text=None,
        title="Police publish figures",
        canonical_url="https://example.test/b",
    )

    assert first != second


def test_the_headline_key_folds_case_and_spacing() -> None:
    assert headline_key(publisher="BBC News", title="A Headline") == headline_key(
        publisher="bbc  news", title="a headline"
    )


def test_the_headline_key_needs_both_halves() -> None:
    assert headline_key(publisher=None, title="A Headline") is None
    assert headline_key(publisher="BBC News", title=None) is None


def test_the_same_row_in_two_packages_gets_two_identifiers() -> None:
    """B-S9A.7. Row `42` of two datasets is two records, not one."""
    first = datapack_source_item_id(provider="p", name="alpha", version="1", row_id="42")
    second = datapack_source_item_id(provider="p", name="beta", version="1", row_id="42")

    assert first != second


def test_two_versions_of_one_dataset_do_not_collide() -> None:
    first = datapack_source_item_id(provider="p", name="alpha", version="1", row_id="42")
    second = datapack_source_item_id(provider="p", name="alpha", version="2", row_id="42")

    assert first != second


# -- context --------------------------------------------------------------


def test_absent_context_fields_are_omitted_rather_than_emptied() -> None:
    """A key that is not present says "not collected"; `""` would say
    "collected and empty"."""
    assembled = assemble_context(ContentContext(title="A title", parent_text=None))

    assert assembled == {"title": "A title"}
    assert "parent_text" not in assembled


def test_context_fields_are_bounded() -> None:
    limit = CONTEXT_FIELD_LIMITS["parent_text"]

    assembled = assemble_context(ContentContext(parent_text="x " * (limit * 2)))

    assert len(assembled["parent_text"]) <= limit + 1


# -- encryption -----------------------------------------------------------


def _key() -> str:
    return base64.b64encode(b"\x01" * KEY_LENGTH_BYTES).decode()


def test_permitted_original_text_round_trips() -> None:
    cipher = ContentCipher.from_base64(_key())

    assert cipher.decrypt(cipher.encrypt("original wording")) == "original wording"


def test_encrypting_twice_produces_different_ciphertext() -> None:
    """A repeated nonce under one key breaks AES-GCM completely."""
    cipher = ContentCipher.from_base64(_key())

    assert cipher.encrypt("same") != cipher.encrypt("same")


def test_a_tampered_row_fails_to_decrypt() -> None:
    """Authenticated encryption, so edited ciphertext is refused rather than
    returning attacker-chosen text to a classifier."""
    cipher = ContentCipher.from_base64(_key())
    stored = bytearray(cipher.encrypt("original wording"))
    stored[-1] ^= 0xFF

    with pytest.raises(ContentEncryptionError):
        cipher.decrypt(bytes(stored))


def test_a_wrong_length_key_is_refused() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        ContentCipher(b"too short")


def test_no_key_disables_retention_rather_than_storing_plaintext() -> None:
    assert build_cipher(None) is None
    assert build_cipher("") is None
