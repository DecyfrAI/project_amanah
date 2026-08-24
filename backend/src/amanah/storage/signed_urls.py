"""Short-lived signed URLs for private objects (B-S26.3, ADR 0007).

ADR 0007 requires the image corpus to be reachable only through a link that
expires. The provider mints those links, not this module.

An earlier implementation signed its own HMAC over the path and expiry using the
content-encryption key, and returned a URL under Supabase's `/object/authenticated`
route. That URL could never work: Supabase does not know that signature, the
`authenticated` route expects an `Authorization` header rather than query
parameters, and the signing key was not a Storage credential at all. It looked
like a signed URL and authenticated nothing.

So signing is now a call to the provider's own signing endpoint, and the returned
token is the provider's. The consequence worth stating: minting a link is I/O and
can fail, where before it was a pure function that always "succeeded" â€” at
producing something unusable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from amanah.ingestion.contract import AdapterError
from amanah.ingestion.http import (
    ClientFactory,
    HttpLimits,
    http_client,
    raise_for_status,
    request_bounded,
)
from amanah.settings import Settings

logger = logging.getLogger(__name__)

#: Supabase's signing endpoint for one private object.
_SIGN_PATH = "/storage/v1/object/sign"


class SigningUnavailableError(RuntimeError):
    """No Storage credential is configured, so no private object can be served.

    Raised rather than returning an unsigned URL: a link that skipped signing
    because a credential was missing would be a permanent public link, and
    failing loudly is the only safe answer.
    """


@dataclass(frozen=True, slots=True)
class SignedUrl:
    """A minted link and the moment it stops working."""

    url: str
    expires_at: datetime


class ObjectUrlSigner:
    """Mints expiring links to private storage paths through the provider API."""

    def __init__(
        self,
        *,
        supabase_url: str,
        storage_secret_key: str,
        bucket: str,
        ttl_seconds: int,
        limits: HttpLimits,
        client_factory: ClientFactory = http_client,
    ) -> None:
        self._supabase_url = supabase_url.rstrip("/")
        self._storage_secret_key = storage_secret_key
        self._bucket = bucket
        self._ttl_seconds = ttl_seconds
        self._limits = limits
        self._client_factory = client_factory

    @classmethod
    def from_settings(
        cls, settings: Settings, *, client_factory: ClientFactory | None = None
    ) -> ObjectUrlSigner:
        """Build a signer, or refuse when no Storage credential is configured.

        The factory is resolved here rather than bound as a default argument, so
        the transport seam is reachable from a test that has not been handed the
        constructor.
        """
        key = settings.supabase_storage_secret_key
        if key is None:
            raise SigningUnavailableError("no Supabase service-role key is configured")
        return cls(
            supabase_url=settings.supabase_url,
            storage_secret_key=key.get_secret_value(),
            bucket=settings.supabase_storage_bucket,
            ttl_seconds=settings.storage_signed_url_ttl_seconds,
            limits=HttpLimits.from_settings(settings),
            client_factory=client_factory or http_client,
        )

    def sign(self, storage_path: str, *, lifetime: timedelta | None = None) -> SignedUrl:
        """Mint a link to one private object through Supabase Storage.

        Raises `AdapterError` when the provider refuses. The caller treats that
        as "the catalogue is unavailable"; it must never fall back to an
        unsigned link.
        """
        ttl = int(lifetime.total_seconds()) if lifetime is not None else self._ttl_seconds
        path = quote(storage_path.lstrip("/"), safe="/")
        url = f"{self._supabase_url}{_SIGN_PATH}/{quote(self._bucket, safe='')}/{path}"

        with self._client_factory(self._limits) as client:
            response = request_bounded(
                client,
                "POST",
                url,
                limits=self._limits,
                headers=self._headers(),
                json_body={"expiresIn": ttl},
            )
        raise_for_status(response)

        signed_path = _read_signed_path(response.content)
        return SignedUrl(
            # Supabase returns a storage-relative path such as
            # `/object/sign/<bucket>/<key>?token=...`. Joining it to the project
            # URL under `/storage/v1` yields the absolute link a browser loads.
            url=f"{self._supabase_url}/storage/v1{signed_path}",
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        )

    def _headers(self) -> dict[str, str]:
        """Service-role credential in a header, never in a URL.

        A credential in a query string is captured by every proxy and access log
        between here and the provider.
        """
        return {
            "Authorization": f"Bearer {self._storage_secret_key}",
            "apikey": self._storage_secret_key,
            "Content-Type": "application/json",
        }


def _read_signed_path(body: bytes) -> str:
    """Extract `signedURL` from the provider's answer.

    A malformed answer is an `AdapterError` rather than a `KeyError`: the caller
    already handles adapter failures as "unavailable", and the raw provider body
    must not travel any further than this function.
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AdapterError("storage_sign_unreadable", is_retryable=False) from exc

    signed = payload.get("signedURL") if isinstance(payload, dict) else None
    if not isinstance(signed, str) or not signed:
        logger.warning("storage signing returned no url")
        raise AdapterError("storage_sign_missing_url", is_retryable=False)
    return signed if signed.startswith("/") else f"/{signed}"
