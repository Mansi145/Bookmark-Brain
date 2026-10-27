"""The Limit reached dialog's "Notify the maintainer": one email per user per day, via Resend.

Resend is faked with httpx.MockTransport (`resend`), so no test sends a real email.
"""

import json

import httpx
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import AiUsage
from app.services import mail
from tests.conftest import TestSession
from tests.test_summaries import summarise
from tests.test_sync import CHROME, feed, item, sync

HOST = "http://93.184.216.34"


class FakeResend:
    """Records the emails it's asked to send; answers `status` (200 = sent)."""

    def __init__(self):
        self.sent: list[dict] = []
        self.status = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert str(request.url) == mail.RESEND_API
        assert request.headers["Authorization"] == "Bearer re_test"
        if self.status != 200:
            return httpx.Response(self.status, json={"message": "Resend is down"})
        self.sent.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "email-1"})


@pytest.fixture
def resend(monkeypatch) -> FakeResend:
    fake = FakeResend()
    settings = get_settings()
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "maintainer_email", "owner@example.com")
    monkeypatch.setattr(
        mail, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    )
    return fake


def hit_the_limit(client, monkeypatch):
    """A limit of 0: the first Summarise is refused, as on a day the user used it all up."""
    monkeypatch.setattr(get_settings(), "ai_daily_limit_per_user", 0)
    sync(client, CHROME, [item("1", HOST + "/a")], full=True)
    assert summarise(client, feed(client)["items"][0]["id"]).status_code == 429


def notify(client) -> httpx.Response:
    return client.post("/api/usage/notify-maintainer")


async def usage_row() -> AiUsage:
    async with TestSession() as session:
        return await session.scalar(select(AiUsage))


async def test_emails_the_maintainer_who_hit_the_limit_and_when(client, resend, monkeypatch):
    hit_the_limit(client, monkeypatch)
    reached = (await usage_row()).limit_reached_at
    assert reached is not None

    assert notify(client).status_code == 204
    [email] = resend.sent
    assert email["to"] == ["owner@example.com"]
    assert email["reply_to"] == "ada@example.com"
    assert "ada (ada@example.com) reached today's AI limit" in email["text"]
    assert f"Hit the limit: {reached:%Y-%m-%d %H:%M} UTC" in email["text"]
    assert (await usage_row()).maintainer_notified_at is not None


async def test_one_email_per_user_per_day(client, resend, monkeypatch):
    hit_the_limit(client, monkeypatch)
    assert notify(client).status_code == 204
    # Pressed again (or the dialog opened again): same answer, no second email.
    assert notify(client).status_code == 204
    assert len(resend.sent) == 1


async def test_only_when_the_limit_is_reached(client, resend):
    response = notify(client)
    assert response.status_code == 409
    assert resend.sent == []


async def test_off_without_a_resend_key(client, resend, monkeypatch):
    hit_the_limit(client, monkeypatch)
    monkeypatch.setattr(get_settings(), "resend_api_key", "")
    response = notify(client)
    assert response.status_code == 503
    assert response.json()["detail"] == "Email isn't set up"


async def test_a_failed_send_can_be_tried_again(client, resend, monkeypatch):
    hit_the_limit(client, monkeypatch)
    resend.status = 500
    assert notify(client).status_code == 502
    assert (await usage_row()).maintainer_notified_at is None

    resend.status = 200
    assert notify(client).status_code == 204
    assert len(resend.sent) == 1


def test_needs_sign_in(anon_client):
    assert notify(anon_client).status_code == 401
