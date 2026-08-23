"""Safe retrieval of a user-supplied public URL (B-S11).

This is the most dangerous input the product accepts: an authenticated user hands
the server an address and asks it to make a request. Everything here exists to
keep that request from becoming a way to read the private network the server sits
in.

The defence has four layers, and each one covers a hole the previous leaves:

1. **Syntax.** Only `http` and `https`, no credentials in the URL, no unusual
   ports. Rejected before any name is resolved.
2. **Resolution.** Every address the host resolves to is checked against the
   private, loopback, link-local, and reserved ranges — *all* of them, not just
   the first, because a name that returns one public and one private address
   would otherwise pass.
3. **Every hop.** Redirects are followed manually and each destination goes
   through steps 1 and 2 again. An automatic follow is precisely how an allowed
   URL turns into a request to `169.254.169.254`.
4. **Response.** A content-type allowlist and a byte budget, so a permitted host
   cannot answer with a gigabyte or with something that is not a document.

One hole is left open and is worth naming: between resolving a name and
connecting to it, the DNS answer could change (a rebinding attack). Closing it
completely means pinning the resolved address into the connection itself. What is
here — re-resolving and re-validating at every hop, with a short total timeout —
raises the cost substantially without that surgery, and the retrieval is bounded
and metadata-only in any case.

Nothing here invokes a shell or a browser. Extraction is `title`/`meta` parsing
over a bounded byte string, and JavaScript is never executed.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlsplit

from amanah.canonical.urls import UrlNormalizationError, normalize_url
from amanah.domain.enums import SubmissionStatus
from amanah.ingestion.http import ClientFactory, HttpLimits, http_client, read_bounded
from amanah.ingestion.urls.extract import PageMetadata, extract_metadata
from amanah.settings import Settings

logger = logging.getLogger(__name__)

#: The only ports a public document is served from. Everything else — databases,
#: caches, admin panels, mail — is refused before a connection is attempted.
PERMITTED_PORTS = frozenset({80, 443, 8080, 8443})

#: Document types worth extracting metadata from. An image, an archive, or an
#: executable has nothing this product needs and plenty it does not want.
PERMITTED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})

#: Statuses that mean "there is a page here, but you are not being shown it".
#: A paywall is a normal outcome for a news URL, not a failure to retry.
_PAYWALL_STATUSES = frozenset({401, 402, 403, 451})


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """The typed outcome of one retrieval attempt (B-S11.6).

    `status` is the same controlled vocabulary a contribution carries, so the
    submission history shows the user exactly what happened without a second
    mapping in between.
    """

    status: SubmissionStatus
    canonical_url: str | None = None
    safe_error_code: str | None = None
    metadata: PageMetadata | None = None
    retrieved_at: datetime | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_analyzed(self) -> bool:
        return self.status is SubmissionStatus.analyzed


def _rejected(code: str) -> RetrievalResult:
    return RetrievalResult(status=SubmissionStatus.rejected, safe_error_code=code)


def _inaccessible(code: str, url: str) -> RetrievalResult:
    return RetrievalResult(
        status=SubmissionStatus.inaccessible, canonical_url=url, safe_error_code=code
    )


def is_public_address(address: str) -> bool:
    """Whether an IP literal is a routable public address.

    Every non-public category is refused explicitly rather than by listing the
    private ranges: loopback, link-local (which is where cloud metadata services
    live), multicast, reserved, and unspecified are all ways to reach something
    that is not a public document.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        # `::ffff:127.0.0.1` is loopback wearing a different notation.
        parsed = parsed.ipv4_mapped
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def resolve_public_addresses(host: str) -> tuple[str, ...]:
    """Resolve a host, refusing unless *every* answer is public.

    All answers, not the one that will be used: a host that resolves to a public
    address and a private one is an attack, and picking the first would make the
    outcome depend on resolver ordering.
    """
    try:
        answers = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return ()
    addresses = tuple({str(answer[4][0]) for answer in answers})
    if not addresses or not all(is_public_address(address) for address in addresses):
        return ()
    return addresses


def validate_destination(raw_url: str) -> str | tuple[SubmissionStatus, str]:
    """Check one URL, returning the normalized form or a typed refusal.

    Used for the submitted URL and again for every redirect destination, which is
    the whole point: a check performed once, before a chain of redirects, checks
    nothing about where the request actually ends up.
    """
    try:
        url = normalize_url(raw_url)
    except UrlNormalizationError:
        return (SubmissionStatus.rejected, "url_not_public_http")

    parts = urlsplit(url)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if port not in PERMITTED_PORTS:
        return (SubmissionStatus.rejected, "url_port_not_permitted")

    # An IP literal skips DNS entirely, so it is checked directly. This is the
    # case that catches `http://127.0.0.1`, `http://[::1]`, and the decimal and
    # octal spellings of the same address.
    literal = as_ip_literal(host)
    if literal is not None:
        if not is_public_address(str(literal)):
            return (SubmissionStatus.rejected, "url_destination_not_public")
        return url

    if not resolve_public_addresses(host):
        return (SubmissionStatus.rejected, "url_destination_not_public")
    return url


def as_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse a host as an IP address in any spelling a resolver would accept.

    `127.0.0.1` is the obvious one. `2130706433`, `0177.0.0.1`, and `127.1` are
    the same address written to get past a check that only recognises dotted
    quads, and every one of them connects. `inet_aton` is the authority for the
    legacy forms because it is the same parser the platform itself uses.

    Returns `None` when the host is a name, in which case it has to be resolved.
    """
    candidate = host.strip("[]")
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        pass
    if candidate.isdigit():
        # A bare integer is a valid IPv4 address to every resolver.
        try:
            return ipaddress.IPv4Address(int(candidate))
        except (ipaddress.AddressValueError, ValueError):
            return None
    try:
        packed = socket.inet_aton(candidate)
    except OSError:
        return None
    return ipaddress.IPv4Address(packed)


class SafeUrlFetcher:
    """Retrieves a public document, or explains precisely why it did not."""

    def __init__(self, settings: Settings, *, client_factory: ClientFactory = http_client) -> None:
        self._limits = HttpLimits.from_settings(settings)
        self._max_redirects = settings.http_max_redirects
        self._client_factory = client_factory

    def retrieve(self, submitted_url: str) -> RetrievalResult:
        """Fetch one URL and extract permitted metadata.

        Returns a typed result for every outcome. Nothing raises: a submission
        that cannot be retrieved is a state the user is shown, not an error the
        API swallows.
        """
        checked = validate_destination(submitted_url)
        if isinstance(checked, tuple):
            status, code = checked
            logger.info("url submission rejected", extra={"safe_error_code": code})
            return RetrievalResult(status=status, safe_error_code=code)

        url = checked
        with self._client_factory(self._limits) as client:
            for _hop in range(self._max_redirects + 1):
                try:
                    response = read_bounded(client, url, limits=self._limits)
                except Exception as exc:
                    logger.warning("url retrieval failed", exc_info=exc)
                    return _inaccessible("retrieval_failed", url)

                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        return _inaccessible("redirect_without_target", url)
                    # Re-validate the destination. This is the check an automatic
                    # redirect-follower skips, and skipping it is how an allowed
                    # URL becomes a request to a private address.
                    revalidated = validate_destination(_absolute(url, location))
                    if isinstance(revalidated, tuple):
                        _status, code = revalidated
                        return _rejected(code)
                    url = revalidated
                    continue

                return self._interpret(url, response)

        return _inaccessible("too_many_redirects", url)

    def _interpret(self, url: str, response: object) -> RetrievalResult:
        status_code = getattr(response, "status_code", 0)
        content_type = getattr(response, "content_type", "")
        content = getattr(response, "content", b"")

        if status_code in _PAYWALL_STATUSES:
            # `spec.md` section 17.2: keep the publisher link and mark the
            # content inaccessible. The submission stays visible in the user's
            # history rather than disappearing.
            return _inaccessible("content_inaccessible", url)
        if status_code == 404:
            return _inaccessible("content_not_found", url)
        if not 200 <= status_code < 300:
            return _inaccessible("retrieval_failed", url)
        if content_type not in PERMITTED_CONTENT_TYPES:
            return RetrievalResult(
                status=SubmissionStatus.unsupported,
                canonical_url=url,
                safe_error_code="content_type_unsupported",
            )

        metadata = extract_metadata(content, url=url)
        warnings: tuple[str, ...] = ()
        if metadata.title is None:
            # Partial extraction: store what is there and say so, rather than
            # inventing a title from the URL.
            warnings = ("No title could be extracted from this page.",)
        return RetrievalResult(
            status=SubmissionStatus.analyzed,
            canonical_url=url,
            metadata=metadata,
            retrieved_at=datetime.now(UTC),
            warnings=warnings,
        )


def _absolute(base: str, location: str) -> str:
    """Resolve a redirect target against the URL that produced it."""
    from urllib.parse import urljoin

    return urljoin(base, location)
