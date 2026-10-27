"""Send an email through Resend (https://resend.com), for "Notify the maintainer".

Resend's API is one HTTPS POST with an API key, so there's no SMTP server to set up. The free
plan sends 100 emails a day, far more than this needs: at most one email per user per day,
and only on days they hit the AI limit.

This isn't the safe fetcher (services/fetch.py): that one is for user-supplied URLs, and this
only ever calls Resend's fixed address.
"""

import httpx

from app.config import get_settings

RESEND_API = "https://api.resend.com/emails"
TIMEOUT_SECONDS = 10.0


class EmailNotSent(Exception):
    """Resend refused the email or couldn't be reached."""


def configured() -> bool:
    settings = get_settings()
    return bool(settings.resend_api_key and settings.maintainer_email)


def _client() -> httpx.AsyncClient:
    """Tests replace this with a client on an httpx.MockTransport, so they never send email."""
    return httpx.AsyncClient(timeout=TIMEOUT_SECONDS)


async def send_to_maintainer(*, subject: str, text: str, reply_to: str | None = None) -> None:
    """Email MAINTAINER_EMAIL a plain-text message. Raises EmailNotSent if it didn't go."""
    settings = get_settings()
    message = {
        "from": settings.email_from,
        "to": [settings.maintainer_email],
        "subject": subject,
        "text": text,
    }
    if reply_to:
        message["reply_to"] = reply_to
    try:
        async with _client() as client:
            response = await client.post(
                RESEND_API,
                json=message,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
    except httpx.HTTPError as e:
        raise EmailNotSent(f"couldn't reach Resend: {e.__class__.__name__}") from e
    if response.status_code >= 400:
        # Resend explains what's wrong (bad key, unverified address, daily quota) in the body.
        raise EmailNotSent(f"Resend answered {response.status_code}: {response.text[:300]}")
