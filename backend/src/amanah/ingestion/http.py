"""The one outbound HTTP boundary (B-S9.5, B-S10.6, B-S11.4).

Every provider call the service makes goes through here, so the limits are in one
place and cannot be forgotten by the next adapter. None of them is optional:
there is no "no timeout" value and no "read the whole thing" mode, because a
provider that hangs or answers with a gigabyte is a real failure mode and not a
hypothetical one.

The response body is read **in chunks against a byte budget** rather than with a
single `.read()`. That distinction matters: a size limit checked after the fact
has already allocated the memory it was meant to prevent, and `Content-Length` is
a claim by the server rather than a fact about what it will send.

Redirects are not followed automatically. Adapters that need them re-validate
each hop themselves (`amanah.ingestion.urls.safe_fetch`), because an automatic
follow is exactly how an allowed URL becomes a request to a private address.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass

import httpx2

from amanah.ingestion.contract import AdapterError
from amanah.settings import Settings

logger = logging.getLogger(__name__)

#: Identifies this service to publishers, as the reviewed feed terms ask. It
#: names the project and a contact path rather than impersonating a browser.
USER_AGENT = "ProjectAmanahBot/1.0 (+https://example.invalid/amanah; research monitoring)"

#: Status codes worth trying again. Everything else — including every `4xx`
#: except these two — is a permanent answer, and retrying it only spends the
#: budget before an operator sees the code.
RETRYABLE_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})

#: Read granularity for the byte budget.
_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class HttpLimits:
    """Bounds one outbound call must respect."""

    connect_timeout_seconds: float
    read_timeout_seconds: float
    total_timeout_seconds: float
    max_response_bytes: int

    @classmethod
    def from_settings(cls, settings: Settings) -> HttpLimits:
        return cls(
            connect_timeout_seconds=settings.http_connect_timeout_seconds,
            read_timeout_seconds=settings.http_read_timeout_seconds,
            total_timeout_seconds=settings.http_total_timeout_seconds,
            max_response_bytes=settings.http_max_response_bytes,
        )


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """A bounded response, already fully read."""

    status_code: int
    headers: Mapping[str, str]
    content: bytes
    url: str

    @property
    def content_type(self) -> str:
        """The media type alone, without parameters and in lower case."""
        return self.headers.get("content-type", "").split(";")[0].strip().lower()


class ResponseTooLargeError(AdapterError):
    """The provider sent more than the byte budget allowed."""

    def __init__(self) -> None:
        super().__init__("response_too_large", is_retryable=False)


#: How a component obtains its bounded client. Injectable so a test can supply a
#: transport without patching module state: the seam is the *transport*, which is
#: the real external boundary, and everything above it still runs for real.
type ClientFactory = Callable[[HttpLimits], AbstractContextManager[httpx2.Client]]


@contextmanager
def http_client(limits: HttpLimits) -> Iterator[httpx2.Client]:
    """Yield a client bound by `limits`, closed on the way out."""
    timeout = httpx2.Timeout(
        limits.total_timeout_seconds,
        connect=limits.connect_timeout_seconds,
        read=limits.read_timeout_seconds,
    )
    client = httpx2.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        yield client
    finally:
        client.close()


def read_bounded(
    client: httpx2.Client,
    url: str,
    *,
    limits: HttpLimits,
    headers: Mapping[str, str] | None = None,
) -> HttpResponse:
    """Perform one GET and read at most `limits.max_response_bytes`.

    Raises `AdapterError` with a stable code and a retry judgement rather than
    letting a transport exception escape: whether a failure is worth retrying is
    a decision this boundary is in the best position to make, and the job state
    machine downstream needs the answer, not the exception.
    """
    try:
        with client.stream("GET", url, headers=dict(headers or {})) as response:
            body = bytearray()
            for chunk in response.iter_bytes(_CHUNK_BYTES):
                body.extend(chunk)
                if len(body) > limits.max_response_bytes:
                    # Stop reading rather than truncating a body we already
                    # allocated in full.
                    raise ResponseTooLargeError
            return HttpResponse(
                status_code=response.status_code,
                headers={key.lower(): value for key, value in response.headers.items()},
                content=bytes(body),
                url=str(response.url),
            )
    except httpx2.TimeoutException as exc:
        raise AdapterError("provider_timeout", is_retryable=True) from exc
    except httpx2.TransportError as exc:
        raise AdapterError("provider_unreachable", is_retryable=True) from exc
    except httpx2.HTTPError as exc:
        # A protocol-level fault. The provider's own message stays in the logs,
        # because it can carry harmful content or an internal host name.
        logger.warning("provider request failed", exc_info=exc)
        raise AdapterError("provider_request_failed", is_retryable=True) from exc


def raise_for_status(response: HttpResponse) -> None:
    """Convert an unsuccessful status into a classified adapter error."""
    if 200 <= response.status_code < 300:
        return
    if response.status_code in RETRYABLE_STATUSES:
        raise AdapterError("provider_unavailable", is_retryable=True)
    if response.status_code in {401, 403}:
        # Not a bug to retry around: access is gated, and `spec.md` section 17.2
        # says show `Access required` and do not scrape.
        raise AdapterError("provider_access_required", is_policy_block=True)
    if response.status_code == 404:
        raise AdapterError("provider_item_missing", is_retryable=False)
    raise AdapterError("provider_rejected_request", is_retryable=False)
