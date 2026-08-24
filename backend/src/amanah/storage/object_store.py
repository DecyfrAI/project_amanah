"""Reading and writing bytes in private object storage (B-S26.2, B-S28.6).

Supabase Storage over the same bounded HTTP transport every other outbound call
uses, so the byte budget and the timeouts cannot drift from the rest of the
service. The storage credential stays in a request header and never reaches a
URL, where a proxy log would capture it.

`build_object_reader` returns a plain callable rather than a client object,
because its one consumer needs exactly "give me these bytes". Writing and
deleting have a small class instead: an upload has to be undone when the row it
belongs to cannot be written, so those two operations are used together.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from amanah.ingestion.contract import AdapterError
from amanah.ingestion.http import (
    ClientFactory,
    HttpLimits,
    http_client,
    raise_for_status,
    read_bounded,
    request_bounded,
)
from amanah.ml.image_classification import ObjectReader
from amanah.settings import Settings
from amanah.storage.signed_urls import SigningUnavailableError

logger = logging.getLogger(__name__)

#: Where Supabase serves private objects to a credentialed caller.
_OBJECT_PATH = "/storage/v1/object"


class ObjectStore:
    """Writes and removes private objects.

    Reading stays a standalone callable (`build_object_reader`) because the
    classification service depends on that capability alone; writing and
    deleting travel together, since a failed database write has to take its
    orphaned object with it.
    """

    def __init__(
        self,
        *,
        supabase_url: str,
        storage_secret_key: str,
        bucket: str,
        limits: HttpLimits,
        client_factory: ClientFactory = http_client,
    ) -> None:
        self._base_url = f"{supabase_url.rstrip('/')}{_OBJECT_PATH}"
        self._token = storage_secret_key
        self._bucket = bucket
        self._limits = limits
        self._client_factory = client_factory

    @classmethod
    def from_settings(
        cls, settings: Settings, *, client_factory: ClientFactory | None = None
    ) -> ObjectStore:
        """Build a store, or refuse when no Storage credential is configured.

        The factory is resolved here rather than bound as a default argument, so
        the transport seam is reachable from a test that has not been handed the
        constructor.
        """
        key = settings.supabase_storage_secret_key
        if key is None:
            raise SigningUnavailableError("no Supabase storage secret key is configured")
        return cls(
            supabase_url=settings.supabase_url,
            storage_secret_key=key.get_secret_value(),
            bucket=settings.supabase_storage_bucket,
            limits=HttpLimits.from_settings(settings),
            client_factory=client_factory or http_client,
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    def upload(self, storage_path: str, payload: bytes, *, mime_type: str) -> None:
        """Write one object. Refuses to overwrite an existing key.

        No upsert: the path is a server-generated UUID, so a collision would mean
        something has gone wrong rather than that a caller wants to replace a
        file. Failing is the safer reading of that.
        """
        with self._client_factory(self._limits) as client:
            response = client.post(
                self._url(storage_path),
                headers={**self._headers(), "Content-Type": mime_type},
                content=payload,
            )
        if response.status_code >= 400:
            logger.warning("object upload refused", extra={"status": response.status_code})
            raise AdapterError("object_upload_failed", is_retryable=response.status_code >= 500)

    def delete(self, storage_path: str) -> None:
        """Remove one object. A key that is already gone is not an error."""
        with self._client_factory(self._limits) as client:
            response = request_bounded(
                client,
                "DELETE",
                self._url(storage_path),
                limits=self._limits,
                headers=self._headers(),
            )
        if response.status_code == 404:
            return
        raise_for_status(response)

    def _url(self, storage_path: str) -> str:
        bucket = quote(self._bucket, safe="")
        return f"{self._base_url}/{bucket}/{quote(storage_path.lstrip('/'), safe='/')}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "apikey": self._token}


def build_object_reader(
    settings: Settings, *, client_factory: ClientFactory | None = None
) -> ObjectReader:
    """Return a bounded reader for private objects.

    Requires the dedicated Storage credential. An earlier version presented
    `SUPABASE_JWT_SECRET` here, but that value is the secret used to *verify*
    inbound access tokens — it is not an access token itself, so Storage
    authenticates nothing with it. The two are deliberately separate settings
    now, and their absence is reported rather than papered over.
    """
    key = settings.supabase_storage_secret_key
    if key is None:
        raise SigningUnavailableError("no Supabase service-role key is configured")

    bucket = quote(settings.supabase_storage_bucket, safe="")
    base_url = f"{settings.supabase_url}{_OBJECT_PATH}/{bucket}"
    token = key.get_secret_value()
    limits = HttpLimits.from_settings(settings)
    build_client = client_factory or http_client

    def read(storage_path: str) -> bytes:
        url = f"{base_url}/{quote(storage_path.lstrip('/'), safe='/')}"
        with build_client(limits) as client:
            response = read_bounded(
                client,
                url,
                limits=limits,
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": token,
                },
            )
        raise_for_status(response)
        if not response.content:
            # An empty object is a curation fault. Classifying nothing would
            # produce a label about nothing.
            raise AdapterError("object_empty", is_retryable=False)
        return response.content

    return read
