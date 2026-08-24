"""Turning an uploaded file into bytes this product is willing to store (B-S28.3).

Everything arriving here is hostile input. The filename is attacker-controlled,
the declared `Content-Type` is attacker-controlled, and the declared length is
attacker-controlled â€” so none of the three is trusted for anything. The format is
decided by decoding the bytes, and the size limit is enforced while reading
rather than checked afterwards, because a limit applied after the fact has
already allocated the memory it was meant to prevent.

The output is always a **re-encode**, never the original bytes passed through.
That is what makes metadata removal reliable: rather than enumerating the EXIF,
GPS, XMP, and maker-note tags to strip â€” a list that is wrong the moment a format
adds one â€” the pixels are drawn onto a fresh image and written out, so anything
that was not a pixel is simply absent. It also collapses the polyglot problem: a
file that is simultaneously a valid GIF and a valid HTML document stops being the
second one once it has been through a decoder and an encoder.

Nothing here logs image bytes, dimensions of a failure, or any part of a
filename.
"""

from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass
from typing import BinaryIO, Final

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

#: Formats a caller may upload, and the media type each is stored as. Pillow's
#: format name on the left, because that is what decoding reports; the browser's
#: claim never appears in this mapping.
ACCEPTED_FORMATS: Final[dict[str, str]] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

#: How much is read past the limit before giving up. One byte is enough to know
#: the file is too large; reading more would defeat the point of the cap.
_OVERREAD_BYTES: Final = 1

#: Read granularity while streaming the upload.
_CHUNK_BYTES: Final = 64 * 1024


class ImageRejectedError(Exception):
    """The upload is not something this product will store.

    Carries a stable code rather than a sentence. The code reaches the client in
    a safe error envelope and is chosen so that it never describes the file's
    contents back to whoever sent it.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class CleanedImage:
    """Re-encoded pixels, and the facts worth storing about them."""

    payload: bytes
    mime_type: str
    sha256: str
    byte_size: int
    pixel_width: int
    pixel_height: int


def read_bounded_upload(stream: BinaryIO, *, max_bytes: int) -> bytes:
    """Read at most `max_bytes`, refusing anything larger.

    Reads one byte beyond the limit deliberately: that is how "exactly at the
    limit" is distinguished from "over it" without trusting a declared length.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    buffer = bytearray()
    while len(buffer) <= max_bytes:
        chunk = stream.read(_CHUNK_BYTES)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes + _OVERREAD_BYTES:
            break

    if len(buffer) > max_bytes:
        raise ImageRejectedError("image_too_large")
    if not buffer:
        raise ImageRejectedError("image_empty")
    return bytes(buffer)


def clean_image(
    payload: bytes,
    *,
    max_pixels: int,
    max_dimension: int,
) -> CleanedImage:
    """Decode, bound, re-encode, and digest one uploaded image.

    Raises `ImageRejectedError` with a stable code for anything that is not a
    bounded, decodable image in an accepted format.
    """
    # Pillow's own decompression-bomb guard, set from configuration rather than
    # left at the library default so the bound is one this deployment chose.
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        image_format, size = _inspect(payload)
        _check_dimensions(size, max_pixels=max_pixels, max_dimension=max_dimension)
        cleaned, mime_type, dimensions = _reencode(payload, image_format)
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit

    return CleanedImage(
        payload=cleaned,
        mime_type=mime_type,
        sha256=hashlib.sha256(cleaned).hexdigest(),
        byte_size=len(cleaned),
        pixel_width=dimensions[0],
        pixel_height=dimensions[1],
    )


def _inspect(payload: bytes) -> tuple[str, tuple[int, int]]:
    """Identify the format from the bytes, and read the declared size.

    `Image.open` parses the header only, so this rejects a wrong format and reads
    the canvas size *before* anything is decoded into memory.
    """
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            image_format = opened.format
            size = opened.size
    except UnidentifiedImageError as exc:
        raise ImageRejectedError("image_unreadable") from exc
    except Image.DecompressionBombError as exc:
        raise ImageRejectedError("image_too_many_pixels") from exc
    except Exception as exc:
        raise ImageRejectedError("image_unreadable") from exc

    if image_format is None or image_format not in ACCEPTED_FORMATS:
        # The *decoded* format, not the declared one: a PNG named `.jpg` with a
        # `image/gif` content type is judged on what it actually is.
        raise ImageRejectedError("image_format_not_allowed")
    return image_format, size


def _check_dimensions(size: tuple[int, int], *, max_pixels: int, max_dimension: int) -> None:
    """Refuse a canvas too large to decode, before decoding it."""
    width, height = size
    if width <= 0 or height <= 0:
        raise ImageRejectedError("image_unreadable")
    if width > max_dimension or height > max_dimension:
        raise ImageRejectedError("image_dimensions_too_large")
    if width * height > max_pixels:
        raise ImageRejectedError("image_too_many_pixels")


def _reencode(payload: bytes, image_format: str) -> tuple[bytes, str, tuple[int, int]]:
    """Draw the pixels onto a fresh image and write it out.

    The new image is constructed from pixel data alone, so EXIF, GPS, XMP, ICC,
    maker notes, and any trailing non-image payload do not survive. Animation
    does not survive either: the first frame is kept, because a classifier reads
    one frame and an animation is a larger attack surface for no benefit.
    """
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            opened.load()
            frame = opened.convert("RGBA" if image_format in {"PNG", "WEBP"} else "RGB")
            # A fresh canvas rather than `frame` itself: `convert` may return the
            # same object with its `info` dict â€” and therefore its metadata â€”
            # still attached. Copying raw pixel data across leaves every
            # non-pixel chunk behind without having to enumerate them.
            stripped = Image.frombytes(frame.mode, frame.size, frame.tobytes())
            dimensions = stripped.size

            buffer = io.BytesIO()
            if image_format == "JPEG":
                stripped.convert("RGB").save(buffer, format="JPEG", quality=88, optimize=True)
            elif image_format == "PNG":
                stripped.save(buffer, format="PNG", optimize=True)
            else:
                stripped.save(buffer, format="WEBP", quality=88, method=4)
    except Image.DecompressionBombError as exc:
        raise ImageRejectedError("image_too_many_pixels") from exc
    except ImageRejectedError:
        raise
    except Exception as exc:
        logger.info("upload refused during re-encode")
        raise ImageRejectedError("image_unreadable") from exc

    return buffer.getvalue(), ACCEPTED_FORMATS[image_format], dimensions
