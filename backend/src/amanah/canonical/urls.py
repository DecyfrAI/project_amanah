"""Canonical URL handling and the news dedupe key (B-S12.5, B-S9.4).

Two different values come out of one URL and they are not interchangeable.

`canonical_url` is what a reader follows and what the publisher sees in their
referrer log. It keeps the URL usable: same path, same meaningful query, tracking
parameters removed because they identify *our* traffic and not the article.

`canonical_url_key` is the dedupe form. It is never displayed and never
dereferenced; it exists so two feeds of the same outlet that publish the same
article under `http`/`https`, with and without `www.`, with and without a
trailing slash, resolve to one row rather than two — which matters because a
duplicated article silently inflates the denominator of every rate computed over
the table.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit, urlunsplit

#: Parameters that describe the campaign that delivered a link rather than the
#: resource it points at. Removing them is both a dedupe measure and a privacy
#: one: several of these carry a click identifier.
TRACKING_PARAMETERS = frozenset(
    {
        "_hsenc",
        "_hsmi",
        "cmpid",
        "dclid",
        "fbclid",
        "gclid",
        "icid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "mkt_tok",
        "msclkid",
        "ncid",
        "ref",
        "ref_src",
        "s_kwcid",
        "smid",
        "twclid",
        "vero_conv",
        "vero_id",
        "wtmc",
        "yclid",
    }
)

#: Only these two reach the network. `spec.md` section 18 and B-S11.1 both make
#: this a hard boundary rather than a default.
PERMITTED_SCHEMES = frozenset({"http", "https"})

_DEFAULT_PORTS = {"http": 80, "https": 443}

#: Long enough for any real article URL, short enough that an absurd one is
#: rejected before it reaches a database column or a log line.
MAXIMUM_URL_LENGTH = 2048


class UrlNormalizationError(ValueError):
    """The URL is not a usable public HTTP(S) address."""


def _strip_tracking(query: str) -> str:
    """Drop campaign parameters, keeping order and everything else intact."""
    kept = [
        (name, value)
        for name, value in parse_qsl(query, keep_blank_values=True)
        if name.lower() not in TRACKING_PARAMETERS and not name.lower().startswith("utm_")
    ]
    return "&".join(f"{name}={value}" if value else name for name, value in kept)


def normalize_url(raw: str) -> str:
    """Return the storable, followable form of a public HTTP(S) URL.

    Raises rather than returning `None`: a URL that cannot be normalized is a
    rejected input, and silently dropping it would hide the rejection from the
    caller who has to report it.
    """
    candidate = raw.strip()
    if not candidate or len(candidate) > MAXIMUM_URL_LENGTH:
        raise UrlNormalizationError("url is empty or too long")

    parts = urlsplit(candidate)
    scheme = parts.scheme.lower()
    if scheme not in PERMITTED_SCHEMES:
        raise UrlNormalizationError("only http and https are accepted")
    if parts.username or parts.password:
        # Credentials in a URL are both a leak and a redirect trick.
        raise UrlNormalizationError("url must not carry credentials")
    if not parts.hostname:
        raise UrlNormalizationError("url has no host")

    # `urlsplit` strips the brackets from an IPv6 host. They have to go back on,
    # or the rebuilt URL reads as `http://::1/` — which re-parses to *no host at
    # all* and would sail past a destination check looking for a private address.
    host = parts.hostname.lower()
    literal = f"[{host}]" if ":" in host else host
    port = parts.port
    netloc = literal if port is None or port == _DEFAULT_PORTS.get(scheme) else f"{literal}:{port}"
    # The fragment is client-side only: it never reaches the server and two URLs
    # differing only by fragment are the same resource.
    return urlunsplit((scheme, netloc, parts.path or "/", _strip_tracking(parts.query), ""))


def canonical_url_key(url: str) -> str:
    """Reduce a URL to the form used only for duplicate detection.

    Deliberately more aggressive than `normalize_url`: scheme is folded away, a
    leading `www.` is dropped, a trailing slash is dropped, and the remaining
    query parameters are sorted. None of that is safe to *follow* — which is why
    it is a separate value that is never published or dereferenced.
    """
    normalized = normalize_url(url)
    parts = urlsplit(normalized)
    host = parts.netloc.removeprefix("www.")
    path = parts.path.rstrip("/") or "/"
    query = "&".join(
        f"{name}={value}" for name, value in sorted(parse_qsl(parts.query, keep_blank_values=True))
    )
    return f"{host}{path}?{query}" if query else f"{host}{path}"


def safe_url(raw: str | None) -> str | None:
    """Normalize when possible, and return `None` when the URL is unusable.

    For the paths where a missing canonical URL is an acceptable outcome — an
    item that simply has none — rather than an error to report.
    """
    if raw is None:
        return None
    try:
        return normalize_url(raw)
    except UrlNormalizationError:
        return None
