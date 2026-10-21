import pytest

from app.services.urls import is_supported, normalize_url, site_of


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://Example.COM/Post/", "https://example.com/Post"),
        ("https://example.com", "https://example.com/"),
        ("https://example.com:443/a", "https://example.com/a"),
        ("http://example.com:8080/a", "http://example.com:8080/a"),
        ("https://example.com/a#section-2", "https://example.com/a"),
        ("https://example.com/a?utm_source=x&utm_medium=y", "https://example.com/a"),
        ("https://example.com/a?b=2&a=1&fbclid=zzz", "https://example.com/a?a=1&b=2"),
        ("  https://example.com/a  ", "https://example.com/a"),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


def test_keeps_www_and_scheme_distinct():
    assert normalize_url("http://www.example.com/a") == "http://www.example.com/a"


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://example.com", True),
        ("http://example.com", True),
        ("chrome://settings", False),
        ("javascript:alert(1)", False),
        ("file:///home/me/notes.html", False),
    ],
)
def test_is_supported(url, ok):
    assert is_supported(url) is ok


def test_site_of():
    assert site_of("https://www.Blog.example.com/x") == "blog.example.com"
