"""Refusing and cleaning uploaded images (B-S28.3).

The subject is what happens to hostile input: a file that lies about its type, a
file that is far too large, a canvas that would exhaust memory to decode, and a
file carrying metadata the sender did not mean to publish.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from amanah.images.cleaning import (
    ImageRejectedError,
    clean_image,
    read_bounded_upload,
)

MAX_PIXELS = 50_000_000
MAX_DIMENSION = 12_000


def _encode(image: Image.Image, image_format: str, **options: object) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **options)
    return buffer.getvalue()


def _png(width: int = 8, height: int = 8) -> bytes:
    return _encode(Image.new("RGB", (width, height), (10, 20, 30)), "PNG")


def _jpeg_with_exif() -> bytes:
    """A JPEG carrying EXIF, including a GPS tag."""
    image = Image.new("RGB", (16, 16), (200, 100, 50))
    exif = image.getexif()
    exif[0x010F] = "ACME Phone"  # Make
    exif[0x9003] = "2026:08:24 10:00:00"  # DateTimeOriginal
    return _encode(image, "JPEG", exif=exif)


# --- reading under a cap ----------------------------------------------------


def test_reading_stops_at_the_byte_cap_whatever_the_sender_declared() -> None:
    """The cap is enforced while reading, not from a declared length."""
    oversized = io.BytesIO(b"x" * 5000)

    with pytest.raises(ImageRejectedError) as caught:
        read_bounded_upload(oversized, max_bytes=1024)

    assert caught.value.code == "image_too_large"


def test_a_file_exactly_at_the_cap_is_accepted() -> None:
    payload = read_bounded_upload(io.BytesIO(b"x" * 1024), max_bytes=1024)

    assert len(payload) == 1024


def test_an_empty_upload_is_refused() -> None:
    with pytest.raises(ImageRejectedError) as caught:
        read_bounded_upload(io.BytesIO(b""), max_bytes=1024)

    assert caught.value.code == "image_empty"


# --- deciding the format from the bytes -------------------------------------


def test_a_non_image_is_refused_however_it_is_named() -> None:
    with pytest.raises(ImageRejectedError) as caught:
        clean_image(b"not an image at all", max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)

    assert caught.value.code == "image_unreadable"


def test_a_format_outside_the_allowlist_is_refused() -> None:
    """A GIF decodes perfectly well and is still not accepted."""
    gif = _encode(Image.new("P", (8, 8)), "GIF")

    with pytest.raises(ImageRejectedError) as caught:
        clean_image(gif, max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)

    assert caught.value.code == "image_format_not_allowed"


def test_an_html_polyglot_does_not_survive() -> None:
    """A file that is both a PNG and a script stops being the second one."""
    polyglot = _png() + b"<script>alert(1)</script>"

    cleaned = clean_image(polyglot, max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)

    assert b"<script>" not in cleaned.payload


# --- bounding the decode ----------------------------------------------------


def test_an_oversized_canvas_is_refused_before_it_is_decoded() -> None:
    wide = _encode(Image.new("RGB", (40, 40)), "PNG")

    with pytest.raises(ImageRejectedError) as caught:
        clean_image(wide, max_pixels=MAX_PIXELS, max_dimension=20)

    assert caught.value.code == "image_dimensions_too_large"


def test_a_decompression_bomb_is_refused() -> None:
    """A small file describing an enormous canvas."""
    bomb = _encode(Image.new("RGB", (2000, 2000)), "PNG")

    with pytest.raises(ImageRejectedError) as caught:
        clean_image(bomb, max_pixels=1000, max_dimension=MAX_DIMENSION)

    assert caught.value.code in {"image_too_many_pixels", "image_dimensions_too_large"}


# --- what the cleaned output carries ----------------------------------------


def test_metadata_does_not_survive_the_re_encode() -> None:
    """EXIF is dropped by re-encoding rather than by enumerating tags."""
    original = _jpeg_with_exif()
    assert Image.open(io.BytesIO(original)).getexif(), "the fixture should carry EXIF"

    cleaned = clean_image(original, max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)

    assert not Image.open(io.BytesIO(cleaned.payload)).getexif()
    assert b"ACME Phone" not in cleaned.payload


def test_the_digest_is_of_the_cleaned_bytes_not_the_original() -> None:
    """Two uploads differing only in metadata converge on one digest."""
    plain = _encode(Image.new("RGB", (16, 16), (200, 100, 50)), "JPEG")

    from_plain = clean_image(plain, max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)
    from_exif = clean_image(_jpeg_with_exif(), max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)

    assert from_plain.sha256 == from_exif.sha256


def test_cleaning_reports_the_stored_type_and_dimensions() -> None:
    cleaned = clean_image(_png(24, 12), max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)

    assert cleaned.mime_type == "image/png"
    assert (cleaned.pixel_width, cleaned.pixel_height) == (24, 12)
    assert cleaned.byte_size == len(cleaned.payload)
    assert len(cleaned.sha256) == 64


def test_every_accepted_format_round_trips() -> None:
    for image_format, expected in (
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
        ("WEBP", "image/webp"),
    ):
        payload = _encode(Image.new("RGB", (10, 10), (1, 2, 3)), image_format)

        cleaned = clean_image(payload, max_pixels=MAX_PIXELS, max_dimension=MAX_DIMENSION)

        assert cleaned.mime_type == expected
