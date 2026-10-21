"""URL normalisation: decide when two bookmarked URLs are "the same article".

Deliberately conservative: we only drop things that never change which page you
get (tracking params, fragments, default ports, letter case of the host). We do
NOT drop "www." or force https, because some sites serve different content there.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid",
    "igshid", "ref_src", "_hsenc", "_hsmi", "yclid",
}  # fmt: skip
DEFAULT_PORTS = {"http": 80, "https": 443}


def is_supported(url: str) -> bool:
    """Only web pages can be fetched and summarised (not chrome://, javascript:, file:)."""
    return urlsplit(url.strip()).scheme.lower() in DEFAULT_PORTS


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()

    netloc = host
    if parts.port and parts.port != DEFAULT_PORTS.get(scheme):
        netloc = f"{host}:{parts.port}"

    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    ]
    query.sort()

    # Fragment (#section) dropped: it points inside the same page.
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def site_of(url: str) -> str:
    """Display name for the card, e.g. 'example.com'."""
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")
