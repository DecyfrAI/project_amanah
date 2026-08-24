"""Short-lived signed URLs for private objects (B-S26.3, ADR 0007).

ADR 0007 requires the image corpus to be reachable only through a link that
expires. This module mints those links.

The signature is an HMAC over the path *and* the expiry, using the server-side
content-encryption key. Signing both together is what makes the expiry binding: a
signature over the path alone would be a permanent credential with a decorative
timestamp beside it, which is the exact failure a "short-lived" URL is meant to
prevent.

Verification is constant-time. A comparison that returns early leaks how much of
a forged signature was correct, one byte at a time.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

from amanah.settings import Settings

#: How long a minted URL stays valid. Long enough to load a catalog page over a
#: slow connection, short enough that a link copied out of a response is useless
#: by the time it is shared.
DEFAULT_URL_LIFETIME = timedelta(minutes=5)

#: Separates the signed fields so `("ab", "1")` and `("a", "b1")` cannot produce
#: the same signature.
_FIELD_SEPARATOR = "\x00"


class SigningUnavailableError(RuntimeError):
    """No signing key is configured, so no private object can be served.

    Raised rather than returning an unsigned URL: a link that skipped signing
    because a key was missing would be a permanent public link, and failing
    loudly is the only safe answer.
    """


@dataclass(frozen=True, slots=True)
class SignedUrl:
    """A minted link and the moment it stops working."""

    url: str
    expires_at: datetime


class ObjectUrlSigner:
    """Mints and verifies expiring links to private storage paths."""

    def __init__(self, *, secret: bytes, base_url: str) -> None:
        self._secret = secret
        self._base_url = base_url.rstrip("/")

    @classmethod
    def from_settings(cls, settings: Settings) -> ObjectUrlSigner:
        """Build a signer, or refuse when no key is configured."""
        key = settings.content_encryption_key
        if key is None:
            raise SigningUnavailableError("no content encryption key is configured")
        return cls(
            secret=key.get_secret_value().encode("utf-8"),
            base_url=f"{settings.supabase_url}/storage/v1/object/authenticated",
        )

    def sign(self, storage_path: str, *, lifetime: timedelta | None = None) -> SignedUrl:
        """Mint a link to one private object."""
        expires_at = datetime.now(UTC) + (lifetime or DEFAULT_URL_LIFETIME)
        expiry = int(expires_at.timestamp())
        query = urlencode({"expires": expiry, "signature": self._sign(storage_path, expiry)})
        return SignedUrl(
            url=f"{self._base_url}/{quote(storage_path, safe='/')}?{query}",
            expires_at=expires_at,
        )

    def verify(self, storage_path: str, *, expiry: int, signature: str, now: datetime) -> bool:
        """Whether this signature is valid for this path and not yet expired."""
        if now.timestamp() > expiry:
            return False
        return hmac.compare_digest(self._sign(storage_path, expiry), signature)

    def _sign(self, storage_path: str, expiry: int) -> str:
        payload = _FIELD_SEPARATOR.join((storage_path, str(expiry))).encode("utf-8")
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
