"""Encryption of permitted original text at rest (B-S12.1).

`content_items.text_ciphertext` is documented as ciphertext and is excluded from
every authenticated projection. This module is what makes that documentation
true. AES-256-GCM is used so the stored value is authenticated as well as
confidential: a row tampered with in the database fails to decrypt rather than
returning attacker-chosen text to a classifier.

When no key is configured the original text is **not stored at all**. That is the
deliberate choice: writing plaintext into a column the schema calls ciphertext
would be worse than storing nothing, because every later reader — including a
future export — would trust the name. Normalized model text and the permitted
excerpt are unaffected, so the pipeline still works; the item simply carries no
retained original.
"""

from __future__ import annotations

import base64
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

#: AES-256.
KEY_LENGTH_BYTES = 32

#: 96 bits is the nonce size AES-GCM is specified for; anything else forces the
#: implementation to hash the nonce first and loses the security proof.
NONCE_LENGTH_BYTES = 12

#: Version prefix on every stored value, so a future key rotation or algorithm
#: change can tell old ciphertext from new instead of guessing.
_VERSION = b"\x01"


class ContentEncryptionError(RuntimeError):
    """The stored value could not be decrypted.

    Carries no detail: the difference between a wrong key and a tampered row is
    not something a caller needs, and stating it is a small oracle.
    """


class ContentCipher:
    """Encrypts and decrypts permitted original text."""

    def __init__(self, key: bytes) -> None:
        if len(key) != KEY_LENGTH_BYTES:
            raise ValueError("content encryption key must be 32 bytes")
        self._cipher = AESGCM(key)

    @classmethod
    def from_base64(cls, encoded: str) -> ContentCipher:
        """Build a cipher from the base64 form used in configuration."""
        try:
            key = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("content encryption key is not valid base64") from exc
        return cls(key)

    def encrypt(self, plaintext: str) -> bytes:
        """Return `version || nonce || ciphertext` for one string.

        A fresh random nonce per call is required, not merely preferred: reusing
        one under the same key breaks AES-GCM completely.
        """
        nonce = os.urandom(NONCE_LENGTH_BYTES)
        sealed = self._cipher.encrypt(nonce, plaintext.encode("utf-8"), None)
        return _VERSION + nonce + sealed

    def decrypt(self, stored: bytes) -> str:
        """Recover the plaintext, or refuse."""
        if len(stored) <= len(_VERSION) + NONCE_LENGTH_BYTES or stored[:1] != _VERSION:
            raise ContentEncryptionError("stored value is not in a known format")
        nonce = stored[len(_VERSION) : len(_VERSION) + NONCE_LENGTH_BYTES]
        sealed = stored[len(_VERSION) + NONCE_LENGTH_BYTES :]
        try:
            return self._cipher.decrypt(nonce, sealed, None).decode("utf-8")
        except (InvalidTag, UnicodeDecodeError) as exc:
            raise ContentEncryptionError("stored value could not be decrypted") from exc


def build_cipher(encoded_key: str | None) -> ContentCipher | None:
    """Return the configured cipher, or `None` when no key is set.

    A `None` cipher disables retention of original text and nothing else, which
    is the same shape as every other optional connector: the missing credential
    turns off one capability rather than the service.
    """
    if not encoded_key:
        logger.warning(
            "content encryption key is not configured",
            extra={"impact": "permitted original text is not retained"},
        )
        return None
    return ContentCipher.from_base64(encoded_key)
