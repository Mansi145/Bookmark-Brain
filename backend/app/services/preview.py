"""Find a page's preview image (the picture link previews use) in HTML we already downloaded.

Pages declare it in <head> for social sharing:
    <meta property="og:image" content="https://example.com/cover.png">
    <meta name="twitter:image" content="/cover.png">
Only the top story of the newspaper feed shows it (owner's decision). We store the URL; the
reader's browser loads the image from the site, so our server never downloads images.
"""

from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

MAX_URL = 2_000

# Best first: og:image:secure_url is the https copy of og:image when a page gives both.
PREFERENCE = [
    "og:image:secure_url",
    "og:image",
    "og:image:url",
    "twitter:image",
    "twitter:image:src",
]


class _EndOfHead(Exception):
    """Social meta tags live in <head>, so parsing stops there."""


class _ImageMeta(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "body":
            raise _EndOfHead
        if tag != "meta":
            return
        a = {k.lower(): (v or "").strip() for k, v in attrs}
        key = (a.get("property") or a.get("name") or "").lower()
        if key in PREFERENCE and a.get("content"):
            self.found.setdefault(key, a["content"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            raise _EndOfHead


def find_preview_image(html: str, page_url: str) -> str | None:
    """The page's preview image as an absolute http(s) URL, or None if it declares none."""
    parser = _ImageMeta()
    try:
        parser.feed(html)
    except _EndOfHead:
        pass
    for key in PREFERENCE:
        href = parser.found.get(key)
        if not href or href.startswith("data:"):
            continue
        absolute = urljoin(page_url, href)
        if urlsplit(absolute).scheme in ("http", "https") and len(absolute) <= MAX_URL:
            return absolute
    return None
