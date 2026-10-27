"""Picking a site's logo from the <link> tags in its <head>."""

from app.services.icons import default_icon, find_icon

PAGE = "https://blog.example.com/posts/1"


def head(*links: str) -> str:
    return (
        f"<html><head>{''.join(links)}</head><body><link rel='icon' href='/late.png'></body></html>"
    )


def test_prefers_apple_touch_icon_over_small_favicon():
    html = head(
        '<link rel="icon" href="/favicon-16.png" sizes="16x16">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">',
    )
    assert find_icon(html, PAGE) == "https://blog.example.com/apple-touch-icon.png"


def test_prefers_svg_and_resolves_relative_urls():
    html = head(
        '<link rel="shortcut icon" href="favicon.ico">',
        '<link rel="icon" href="//cdn.example.com/logo.svg">',
    )
    assert find_icon(html, PAGE) == "https://cdn.example.com/logo.svg"


def test_skips_safari_mask_icon():
    html = head(
        '<link rel="mask-icon" href="/mask.svg" color="#000">', '<link rel="icon" href="/fav.png">'
    )
    assert find_icon(html, PAGE) == "https://blog.example.com/fav.png"


def test_small_inline_svg_is_kept():
    data = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E"
    assert find_icon(head(f'<link rel="icon" href="{data}">'), PAGE) == data


def test_no_icon_declared():
    assert find_icon(head(), PAGE) is None  # the one in <body> is ignored
    assert default_icon(PAGE) == "https://blog.example.com/favicon.ico"
