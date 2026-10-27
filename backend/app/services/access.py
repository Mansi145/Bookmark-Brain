"""Tell whether a page needs you to be signed in (or subscribed) to read it.

We fetch pages anonymously, so a page that needs your account shows us a sign-in
screen instead of its content. Sites leave recognisable signs:
- they redirect to a sign-in address (/login, /users/sign_in, accounts.google.com…)
- they answer HTTP 401
- the page is a password form with no article
- the address is a logged-in web app (web mail, chat), which renders everything
  with JavaScript and tells us nothing in its HTML
- news sites mark paywalled articles with `"isAccessibleForFree": false`
  (schema.org metadata that search engines read)

Not a sign-in page: a bot challenge (Cloudflare "Just a moment…", HTTP 403). That page
is readable in your browser, we just can't read it from the server.

This can't catch everything (a sign-in wall drawn by JavaScript at a normal address),
but it never needs network calls and errs on the side of "open".
"""

import re
from urllib.parse import urlsplit

from app.services.fetch import FetchedPage

LOGIN = "login"
PAYWALL = "paywall"

# Path pieces that mean "this is a sign-in page" (matched on whole segments).
LOGIN_PATH = re.compile(
    r"/(login|log-in|signin|sign-in|sign_in|servicelogin|sso|auth|oauth2?|authorize)(/|$|\?)",
    re.IGNORECASE,
)
LOGIN_HOST_PREFIXES = ("accounts.", "login.", "signin.", "auth.", "sso.", "id.")

# Logged-in web apps: (host, path prefix). Their HTML is an empty JavaScript shell.
LOGGED_IN_APPS = (
    ("outlook.office.com", "/"),
    ("outlook.office365.com", "/"),
    ("outlook.live.com", "/"),
    ("mail.google.com", "/"),
    ("calendar.google.com", "/"),
    ("docs.google.com", "/"),
    ("drive.google.com", "/"),
    ("web.whatsapp.com", "/"),
    ("app.slack.com", "/"),
    ("teams.microsoft.com", "/"),
    ("discord.com", "/channels"),
    ("www.linkedin.com", "/feed"),
    ("www.linkedin.com", "/messaging"),
)

PASSWORD_FIELD = re.compile(r"<input[^>]+type\s*=\s*[\"']?password", re.IGNORECASE)
NOT_FREE = re.compile(r"[\"']?isAccessibleForFree[\"']?\s*:\s*[\"']?false", re.IGNORECASE)


def looks_like_sign_in_url(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    if host.startswith(LOGIN_HOST_PREFIXES) or LOGIN_PATH.search(path + "/"):
        return True
    return any(host == h and path.startswith(p) for h, p in LOGGED_IN_APPS)


def is_paywalled(html: str) -> bool:
    return bool(NOT_FREE.search(html))


def detect_access(bookmark_url: str, page: FetchedPage | None, has_article: bool) -> str | None:
    """LOGIN, PAYWALL or None (open, or we can't tell)."""
    if page is not None and page.status_code == 401:
        return LOGIN
    html = (page.html if page else None) or ""
    if is_paywalled(html):
        return PAYWALL  # may still have a readable teaser
    if has_article:
        # A readable article isn't a sign-in page, even at an address like /docs/auth/.
        return None
    if looks_like_sign_in_url(bookmark_url) or (page and looks_like_sign_in_url(page.url)):
        return LOGIN  # a sign-in page or logged-in app, or we were redirected to one
    if PASSWORD_FIELD.search(html):
        return LOGIN  # a password form and nothing else
    return None
