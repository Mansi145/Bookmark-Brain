"""Turn a page's HTML into clean article text (what the summariser will read).

A web page is mostly navigation, ads, cookie banners and footers. `trafilatura`
finds the main content block and returns just its text, plus metadata like the
page title and description. Stripping the clutter matters for AI: the model only
sees what helps, and we spend fewer tokens (free-tier quotas are per token).
"""

import math
from dataclasses import dataclass

import trafilatura

MAX_CHARS = 200_000  # plenty for any article; protects the DB from giant pages
WORDS_PER_MINUTE = 230  # a typical adult reading speed for online articles
# Fewer words than this is a sign-in wall, cookie page or placeholder, not an article.
# Not worth storing, and summarising it would waste AI quota.
MIN_WORDS = 50


@dataclass
class Article:
    title: str | None
    description: str | None
    text: str | None  # None when the page has no real article (see MIN_WORDS)
    word_count: int


def extract_article(html: str, url: str) -> Article:
    """Return the main text and metadata of `html`.

    `text` is None if there's no readable article, but the title and description are
    still kept: app-like pages (YouTube, Discord) have no text in their HTML, yet their
    <head> still says what they are.

    CPU-bound (parses the whole page), so async code should run it in a thread.
    """
    doc = trafilatura.bare_extraction(
        html,
        url=url,
        with_metadata=True,
        include_comments=False,  # reader comments aren't the article
        include_tables=True,
        favor_precision=True,  # rather miss a paragraph than include a sidebar
    )
    if doc is None:  # no content block at all: still read <title> and <meta> tags
        meta = trafilatura.extract_metadata(html, default_url=url)
        return Article(
            title=(meta.title if meta else None) or None,
            description=(meta.description if meta else None) or None,
            text=None,
            word_count=0,
        )
    text = (doc.text or "").strip()[:MAX_CHARS]
    word_count = len(text.split())
    is_article = word_count >= MIN_WORDS
    return Article(
        title=doc.title or None,
        description=doc.description or None,
        text=text if is_article else None,
        word_count=word_count if is_article else 0,
    )


def reading_minutes(word_count: int | None) -> int | None:
    """Estimated reading time, rounded up; None if we don't know the length yet."""
    if not word_count:
        return None
    return max(1, math.ceil(word_count / WORDS_PER_MINUTE))
