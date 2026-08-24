"""Reading bytes out of private object storage (B-S26.2).

Supabase Storage over the same bounded HTTP transport every other outbound call
uses, so the byte budget and the timeouts cannot drift from the rest of the
service. The service-role credential stays in a request header and never reaches
a URL, where a proxy log would capture it.

`build_object_reader` returns a plain callable rather than a client object. The
one consumer needs exactly "give me these bytes", and a class would be an
abstraction for a single use.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from amanah.ingestion.contract import AdapterError
from amanah.ingestion.http import HttpLimits, http_client, raise_for_status, read_bounded
from amanah.ml.image_classification import ObjectReader
from amanah.settings import Settings

logger = logging.getLogger(__name__)

#: Where Supabase serves private objects to a service-role caller.
_OBJECT_PATH = "/storage/v1/object"


def build_object_reader(settings: Settings) -> ObjectReader:
    """Return a bounded reader for private objects.

    The Supabase JWT secret doubles as the service credential for storage in this
    deployment, which is why no separate setting is introduced: adding one that
    must always equal an existing one is a second place for a deployment to be
    wrong.
    """
    base_url = f"{settings.supabase_url}{_OBJECT_PATH}"
    token = settings.supabase_jwt_secret.get_secret_value()
    limits = HttpLimits.from_settings(settings)

    def read(storage_path: str) -> bytes:
        url = f"{base_url}/{quote(storage_path, safe='/')}"
        with http_client(limits) as client:
            response = read_bounded(
                client,
                url,
                limits=limits,
                headers={"Authorization": f"Bearer {token}"},
            )
        raise_for_status(response)
        if not response.content:
            # An empty object is a curation fault. Classifying nothing would
            # produce a label about nothing.
            raise AdapterError("object_empty", is_retryable=False)
        return response.content

    return read
