"""Safe user-URL retrieval (B-S11.7).

This is the most dangerous input the product accepts, so these tests are written
adversarially: every case is a way someone might try to turn "analyse this
article" into "make a request to the machine you are running on".

Address validation runs for real. Only the HTTP transport is mocked, and DNS is
only substituted where a test needs a name to resolve somewhere specific — the
`ipaddress` checks, the port list, the scheme list, and the redirect
re-validation are all the production code.
"""

from __future__ import annotations

import socket
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import httpx2
import pytest

from amanah.domain.enums import SubmissionStatus
from amanah.ingestion.http import ClientFactory, HttpLimits
from amanah.ingestion.urls.extract import extract_metadata
from amanah.ingestion.urls.safe_fetch import (
    PERMITTED_CONTENT_TYPES,
    SafeUrlFetcher,
    is_public_address,
    validate_destination,
)
from tests.conftest import make_settings

PAGE = (
    b"<!doctype html><html lang='en'><head>"
    b"<title>Council debates mosque safety</title>"
    b"<meta name='description' content='A short synthetic description.'>"
    b"<meta property='og:site_name' content='Synthetic Wire'>"
    b"<link rel='canonical' href='https://example.test/story'>"
    b"</head><body><p>Body text that must not be stored.</p></body></html>"
)


def _factory(handler: Callable[[httpx2.Request], httpx2.Response]) -> ClientFactory:
    transport = httpx2.MockTransport(handler)

    @contextmanager
    def factory(limits: HttpLimits) -> Iterator[httpx2.Client]:
        del limits
        client = httpx2.Client(transport=transport, follow_redirects=False)
        try:
            yield client
        finally:
            client.close()

    return factory


@pytest.fixture(autouse=True)
def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve every test host to one public address.

    Substituted so the suite does not depend on a network. The validation being
    exercised is what the code does *with* an answer, and the private-address
    cases below supply their own resolver.
    """

    def resolve(host: str, *args: object, **kwargs: object) -> list[object]:
        del args, kwargs
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)


def _fetcher(handler: Callable[[httpx2.Request], httpx2.Response]) -> SafeUrlFetcher:
    return SafeUrlFetcher(make_settings(), client_factory=_factory(handler))


def _ok(request: httpx2.Request) -> httpx2.Response:
    del request
    return httpx2.Response(200, content=PAGE, headers={"content-type": "text/html; charset=utf-8"})


# -- address validation ---------------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "192.168.1.1",
        "172.16.0.1",
        "169.254.169.254",  # cloud instance metadata
        "0.0.0.0",  # noqa: S104 - the unspecified address, listed here to be refused
        "::1",
        "fe80::1",
        "::ffff:127.0.0.1",  # loopback in IPv6 notation
    ],
)
def test_non_public_addresses_are_refused(address: str) -> None:
    assert is_public_address(address) is False


def test_a_routable_address_is_accepted() -> None:
    assert is_public_address("93.184.216.34") is True


@pytest.mark.parametrize(
    "candidate",
    [
        "http://127.0.0.1/admin",
        "http://[::1]/admin",
        "http://2130706433/",  # 127.0.0.1 in decimal
        "http://0177.0.0.1/",  # and in octal
    ],
)
def test_localhost_in_every_spelling_is_rejected(candidate: str) -> None:
    """Each of these is `127.0.0.1` written to get past a naive string check."""
    outcome = validate_destination(candidate)

    assert isinstance(outcome, tuple)
    assert outcome[0] is SubmissionStatus.rejected


def test_an_unsafe_port_is_rejected_before_any_connection() -> None:
    """Databases, caches, and admin panels are not public documents."""
    outcome = validate_destination("http://example.test:6379/")

    assert isinstance(outcome, tuple)
    assert outcome[1] == "url_port_not_permitted"


def test_credentials_in_the_url_are_rejected() -> None:
    outcome = validate_destination("https://user:secret@example.test/story")

    assert isinstance(outcome, tuple)


@pytest.mark.parametrize("scheme", ["file", "ftp", "gopher", "javascript", "data"])
def test_prohibited_schemes_are_rejected(scheme: str) -> None:
    outcome = validate_destination(f"{scheme}://example.test/x")

    assert isinstance(outcome, tuple)
    assert outcome[1] == "url_not_public_http"


def test_a_host_resolving_to_any_private_address_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every answer is checked, not the first: a name returning one public and
    one private address is an attack, and picking the first would make the
    outcome depend on resolver ordering."""

    def mixed(host: str, *args: object, **kwargs: object) -> list[object]:
        del host, args, kwargs
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", mixed)

    outcome = validate_destination("https://rebinding.example.test/story")

    assert isinstance(outcome, tuple)
    assert outcome[1] == "url_destination_not_public"


def test_a_host_that_does_not_resolve_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(host: str, *args: object, **kwargs: object) -> list[object]:
        del host, args, kwargs
        raise socket.gaierror("no such host")

    monkeypatch.setattr(socket, "getaddrinfo", failing)

    assert isinstance(validate_destination("https://nowhere.example.test/"), tuple)


# -- retrieval ------------------------------------------------------------


def test_a_public_page_is_analysed_and_yields_metadata_only() -> None:
    result = _fetcher(_ok).retrieve("https://example.test/story")

    assert result.status is SubmissionStatus.analyzed
    assert result.metadata is not None
    assert result.metadata.title == "Council debates mosque safety"
    assert result.metadata.description == "A short synthetic description."
    # The body is read to find the head, but never retained.
    assert "must not be stored" not in str(result.metadata)


def test_a_redirect_to_a_private_address_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The check an automatic redirect-follower skips, and skipping it is how an
    allowed URL becomes a request to a private address."""
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(str(request.url))
        return httpx2.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})

    result = _fetcher(handler).retrieve("https://example.test/story")

    assert result.status is SubmissionStatus.rejected
    assert result.safe_error_code == "url_destination_not_public"
    # The private destination was never contacted.
    assert all("169.254" not in call for call in calls)


def test_a_redirect_chain_is_bounded() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(302, headers={"location": "https://example.test/next"})

    result = _fetcher(handler).retrieve("https://example.test/story")

    assert result.status is SubmissionStatus.inaccessible
    assert result.safe_error_code == "too_many_redirects"


def test_a_redirect_to_another_public_page_is_followed() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/story":
            return httpx2.Response(301, headers={"location": "https://example.test/final"})
        return _ok(request)

    result = _fetcher(handler).retrieve("https://example.test/story")

    assert result.status is SubmissionStatus.analyzed
    assert result.canonical_url == "https://example.test/final"


def test_an_oversized_response_is_refused() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(200, content=b"x" * 5_000_000, headers={"content-type": "text/html"})

    settings = make_settings(http_max_response_bytes=1024)
    fetcher = SafeUrlFetcher(settings, client_factory=_factory(handler))

    result = fetcher.retrieve("https://example.test/huge")

    assert result.status is SubmissionStatus.inaccessible
    assert result.safe_error_code == "retrieval_failed"


@pytest.mark.parametrize("content_type", ["application/pdf", "image/png", "application/zip"])
def test_an_unsupported_content_type_is_reported_as_unsupported(content_type: str) -> None:
    """The user sees a state, not an error. The submission stays in history."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(200, content=b"...", headers={"content-type": content_type})

    result = _fetcher(handler).retrieve("https://example.test/file")

    assert result.status is SubmissionStatus.unsupported
    assert content_type not in PERMITTED_CONTENT_TYPES


@pytest.mark.parametrize("status", [401, 402, 403, 451])
def test_a_paywall_keeps_the_link_and_marks_the_content_inaccessible(status: int) -> None:
    """`spec.md` section 17.2. A paywall is a normal outcome for a news URL."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(status, content=b"", headers={"content-type": "text/html"})

    result = _fetcher(handler).retrieve("https://example.test/paywalled")

    assert result.status is SubmissionStatus.inaccessible
    assert result.canonical_url == "https://example.test/paywalled"


def test_a_missing_page_is_inaccessible_rather_than_failed() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(404, content=b"", headers={"content-type": "text/html"})

    result = _fetcher(handler).retrieve("https://example.test/gone")

    assert result.safe_error_code == "content_not_found"


def test_a_timeout_is_reported_rather_than_raised() -> None:
    """A submission that cannot be retrieved is a state the user is shown, not
    an exception the API swallows."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=request)

    result = _fetcher(handler).retrieve("https://example.test/slow")

    assert result.status is SubmissionStatus.inaccessible
    assert result.safe_error_code == "retrieval_failed"


def test_partial_extraction_says_so_rather_than_inventing_a_title() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(
            200,
            content=b"<html><body>no head at all</body></html>",
            headers={"content-type": "text/html"},
        )

    result = _fetcher(handler).retrieve("https://example.test/bare")

    assert result.status is SubmissionStatus.analyzed
    assert result.metadata is not None
    assert result.metadata.title is None
    assert result.warnings


# -- extraction -----------------------------------------------------------


def test_malformed_markup_still_yields_what_was_parsed() -> None:
    metadata = extract_metadata(
        b"<html><head><title>Half a page</title><meta name='description'",
        url="https://example.test/x",
    )

    assert metadata.title == "Half a page"


def test_extraction_never_returns_the_article_body() -> None:
    metadata = extract_metadata(PAGE, url="https://example.test/story")

    assert "Body text that must not be stored" not in str(metadata)


def test_a_canonical_link_is_preferred_over_the_requested_url() -> None:
    metadata = extract_metadata(PAGE, url="https://example.test/story?utm_source=x")

    assert metadata.canonical_url == "https://example.test/story"
