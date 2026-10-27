"""Sign-in / paywall detection, from the signs real sites leave."""

import pytest

from app.services.access import LOGIN, PAYWALL, detect_access, looks_like_sign_in_url
from app.services.fetch import FetchedPage


def page(url="https://site.com/post", status=200, html="<html></html>"):
    return FetchedPage(url=url, status_code=status, content_type="text/html", html=html)


@pytest.mark.parametrize(
    "url",
    [
        "https://accounts.google.com/v3/signin/identifier",
        "https://gitlab.example.com/users/sign_in",
        "https://example.com/login?next=/dashboard",
        "https://outlook.office.com/mail/inbox/id/AAQk",
        "https://discord.com/channels/@me",
        "https://mail.google.com/mail/u/0/",
    ],
)
def test_sign_in_addresses(url):
    assert looks_like_sign_in_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://discord.com/",  # the marketing site is public
        "https://blog.example.com/logins-are-hard",  # "login" inside a word, not a segment
        "https://stackoverflow.com/questions/1/how-to-login",
    ],
)
def test_ordinary_addresses(url):
    assert not looks_like_sign_in_url(url)


def test_redirect_to_sign_in_page():
    assert (
        detect_access("https://site.com/private", page(url="https://site.com/login"), False)
        == LOGIN
    )


def test_401_is_login():
    assert detect_access("https://site.com/x", page(status=401, html=None), False) == LOGIN


def test_password_form_without_article():
    form = '<form><input name="user"><input type="password" name="pw"></form>'
    assert detect_access("https://site.com/x", page(html=form), False) == LOGIN


def test_logged_in_app_without_fetching():
    assert detect_access("https://outlook.office.com/mail/", None, False) == LOGIN


def test_paywall_metadata():
    ld = '<script type="application/ld+json">{"isAccessibleForFree": false}</script>'
    assert detect_access("https://news.com/a", page(html=ld), True) == PAYWALL


def test_readable_article_is_open_even_at_auth_address():
    # Docs *about* authentication aren't sign-in pages.
    assert (
        detect_access("https://docs.site.com/auth/", page(url="https://docs.site.com/auth/"), True)
        is None
    )


def test_bot_challenge_is_not_sign_in():
    challenge = page(status=403, html=None)  # Cloudflare "Just a moment..."
    assert detect_access("https://stackoverflow.com/questions/1", challenge, False) is None
