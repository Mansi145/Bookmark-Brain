"""Find a site's logo (favicon) in a page we've already downloaded.

Pages declare their icons in <head>:
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
    <link rel="icon" href="/favicon-32x32.png" sizes="32x32">
    <link rel="shortcut icon" href="/favicon.ico">
We pick the clearest one and store only its URL; the browser loads it from the site and
falls back to a letter tile if it fails. No extra requests from our server.
"""

from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

MAX_DATA_URI = 4_000  # some sites inline a small SVG icon; skip anything bigger


class _EndOfHead(Exception):
    """Icons live in <head>, so parsing stops there."""


class _IconLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.icons: list[tuple[str, str, str]] = []  # (rel, href, sizes)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "link":
            return
        a = {k.lower(): (v or "").strip() for k, v in attrs}
        rel = a.get("rel", "").lower()
        if "icon" in rel and a.get("href"):
            self.icons.append((rel, a["href"], a.get("sizes", "").lower()))

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            raise _EndOfHead


def _score(rel: str, href: str, sizes: str) -> int:
    """Higher is better. Prefer big, colourful icons; avoid single-colour mask icons."""
    if "mask-icon" in rel:
        return -1  # Safari's one-colour outline: looks wrong in a tile
    if href.lower().endswith(".svg") or "any" in sizes:
        return 500  # scales to any size
    biggest = max(
        (int(p.split("x")[0]) for p in sizes.split() if p.split("x")[0].isdigit()), default=0
    )
    if "apple-touch-icon" in rel:
        return 400 + min(biggest, 99)  # usually 180 px and opaque: clear at any size
    return 100 + min(biggest, 299)


def find_icon(html: str, page_url: str) -> str | None:
    """The best icon URL declared in `html` (absolute), or None if it declares none."""
    parser = _IconLinks()
    try:
        parser.feed(html)
    except _EndOfHead:
        pass
    candidates = [(_score(*icon), icon[1]) for icon in parser.icons]
    candidates = [(score, href) for score, href in candidates if score >= 0]
    for _, href in sorted(candidates, reverse=True):
        if href.startswith("data:image/"):
            if len(href) <= MAX_DATA_URI:
                return href
            continue
        absolute = urljoin(page_url, href)
        if urlsplit(absolute).scheme in ("http", "https"):
            return absolute
    return None


def default_icon(page_url: str) -> str | None:
    """Most sites still serve /favicon.ico even when the page doesn't mention it."""
    parts = urlsplit(page_url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    return f"{parts.scheme}://{parts.netloc}/favicon.ico"
