"""GitHub sign-in: the redirect to GitHub, the callback, linking accounts by verified email, and
everything that must be refused (another site's state, a cancelled sign-in, redirects elsewhere).
Then Settings → Sign-in methods: linking Google or GitHub to the signed-in account, and unlinking.

GitHub is faked with httpx.MockTransport (FakeGitHub), so no test calls github.com.
"""

from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.api import auth as auth_api
from app.auth import github
from app.auth.security import SESSION_COOKIE, GoogleIdentity
from app.config import get_settings

APP = "http://localhost:5173"
SETTINGS = "/settings?section=account"


class FakeGitHub:
    """GitHub's token endpoint and API, answering for one user ("ada")."""

    def __init__(self):
        self.profile = {"id": 4242, "login": "ada", "name": "Ada", "avatar_url": "https://a/1"}
        self.emails = [{"email": "ada@example.com", "primary": True, "verified": True}]
        self.calls: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request.url.path)
        if str(request.url) == github.TOKEN_URL:
            form = parse_qs(request.content.decode())
            assert form["client_secret"] == ["test-secret"]
            if form["code"] != ["good-code"]:
                return httpx.Response(200, json={"error": "bad_verification_code"})
            return httpx.Response(200, json={"access_token": "gho_test"})
        assert request.headers["Authorization"] == "Bearer gho_test"
        if request.url.path == "/user":
            return httpx.Response(200, json=self.profile)
        if request.url.path == "/user/emails":
            return httpx.Response(200, json=self.emails)
        return httpx.Response(404)


@pytest.fixture
def fake_github(monkeypatch) -> FakeGitHub:
    fake = FakeGitHub()
    settings = get_settings()
    monkeypatch.setattr(settings, "github_client_id", "test-id")
    monkeypatch.setattr(settings, "github_client_secret", "test-secret")
    monkeypatch.setattr(
        github, "make_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(fake.handle))
    )
    return fake


def start(client, next: str = "/", *, link: bool = False) -> str:
    """Click "Continue with GitHub" (or Link in Settings); returns the state sent to GitHub."""
    path = "/api/auth/github/link" if link else "/api/auth/github"
    response = client.get(path, params={"next": next}, follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(github.AUTHORIZE_URL)
    return parse_qs(urlsplit(location).query)["state"][0]


def finish(client, state: str, **params) -> httpx.Response:
    """GitHub sends the browser back to the callback."""
    params = {"code": "good-code", "state": state} | params
    return client.get("/api/auth/github/callback", params=params, follow_redirects=False)


def test_sends_the_browser_to_github_asking_only_for_identity(anon_client, fake_github):
    response = anon_client.get("/api/auth/github", follow_redirects=False)
    query = parse_qs(urlsplit(response.headers["location"]).query)

    assert query["client_id"] == ["test-id"]
    assert query["redirect_uri"] == ["http://localhost:8000/api/auth/github/callback"]
    assert query["scope"] == ["read:user user:email"]
    assert "bb_github_state" in response.cookies


def test_signs_in_and_comes_back_to_the_page_it_started_on(anon_client, fake_github):
    state = start(anon_client, next="/connect?nonce=abc&browser=chrome")
    response = finish(anon_client, state)

    assert response.headers["location"] == f"{APP}/connect?nonce=abc&browser=chrome"
    assert SESSION_COOKIE in response.cookies
    me = anon_client.get("/api/me").json()
    assert (me["email"], me["name"], me["providers"]) == ("ada@example.com", "Ada", ["github"])


def test_the_same_verified_email_is_the_same_account(anon_client, fake_github, user):
    # `user` signed up with Google as ada@example.com.
    finish(anon_client, start(anon_client))

    me = anon_client.get("/api/me").json()
    assert me["id"] == user.id
    assert me["providers"] == ["google", "github"]


def test_a_different_email_is_a_new_account(anon_client, fake_github, user):
    fake_github.emails = [{"email": "other@example.com", "primary": True, "verified": True}]
    finish(anon_client, start(anon_client))

    assert anon_client.get("/api/me").json()["id"] != user.id


def test_signing_in_again_finds_the_account_by_github_id(anon_client, fake_github):
    finish(anon_client, start(anon_client))
    first = anon_client.get("/api/me").json()

    fake_github.profile["name"] = "Ada L."  # renamed on GitHub: the profile follows
    finish(anon_client, start(anon_client))
    again = anon_client.get("/api/me").json()
    assert (again["id"], again["name"]) == (first["id"], "Ada L.")


def test_an_account_without_a_verified_primary_email_is_refused(anon_client, fake_github):
    fake_github.emails = [
        {"email": "ada@example.com", "primary": True, "verified": False},
        {"email": "ada@work.example", "primary": False, "verified": True},
    ]
    response = finish(anon_client, start(anon_client))

    assert response.headers["location"] == f"{APP}/?github_error=no_email"
    assert SESSION_COOKIE not in response.cookies


def test_a_state_this_browser_didnt_start_is_refused(anon_client, fake_github):
    start(anon_client)
    response = finish(anon_client, "forged-state")

    assert response.headers["location"] == f"{APP}/?github_error=failed"
    assert SESSION_COOKIE not in response.cookies
    assert fake_github.calls == []  # never even asked GitHub for a token


def test_saying_no_on_github(anon_client, fake_github):
    state = start(anon_client, next="/how-it-works")
    response = finish(anon_client, state, code="", error="access_denied")

    assert response.headers["location"] == f"{APP}/how-it-works?github_error=cancelled"


def test_a_code_github_rejects(anon_client, fake_github):
    response = finish(anon_client, start(anon_client), code="stale-code")
    assert response.headers["location"] == f"{APP}/?github_error=failed"


@pytest.mark.parametrize("next", ["//evil.example/", "https://evil.example/", "/\\evil.example"])
def test_never_redirects_to_another_site(anon_client, fake_github, next):
    response = finish(anon_client, start(anon_client, next=next))
    assert response.headers["location"] == f"{APP}/"


def test_says_so_when_github_sign_in_isnt_set_up(anon_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "github_client_id", "")  # whatever backend/.env says
    response = anon_client.get("/api/auth/github", params={"next": "/"}, follow_redirects=False)
    assert response.headers["location"] == f"{APP}/?github_error=unavailable"


def test_google_sign_in_finds_an_account_made_with_github(anon_client, fake_github, monkeypatch):
    finish(anon_client, start(anon_client))
    github_account = anon_client.get("/api/me").json()

    async def fake_verify(credential):
        return GoogleIdentity(
            {"sub": "google-ada", "email": "ada@example.com", "name": "Ada", "picture": None}
        )

    monkeypatch.setattr(auth_api, "verify_google_credential", fake_verify)
    anon_client.cookies.clear()
    me = anon_client.post("/api/auth/google", json={"credential": "token"}).json()
    assert me["id"] == github_account["id"]
    assert me["providers"] == ["google", "github"]


# Settings → Sign-in methods


def google_says(monkeypatch, sub: str, email: str) -> None:
    """Google's button returns a credential for this Google account."""

    async def fake_verify(credential):
        return GoogleIdentity({"sub": sub, "email": email, "name": "Ada G", "picture": None})

    monkeypatch.setattr(auth_api, "verify_google_credential", fake_verify)


def test_linking_github_adds_it_to_the_signed_in_account(client, anon_client, fake_github, user):
    # A different email still links: being signed in and approving on GitHub proves it's one person.
    fake_github.emails = [{"email": "ada@work.example", "primary": True, "verified": True}]
    response = finish(client, start(client, next=SETTINGS, link=True))

    assert response.headers["location"] == f"{APP}{SETTINGS}"
    assert SESSION_COOKIE not in response.cookies  # still the same session
    me = client.get("/api/me").json()
    assert (me["id"], me["providers"]) == (user.id, ["google", "github"])
    assert (me["email"], me["name"]) == ("ada@example.com", "ada")  # linking isn't signing in

    finish(anon_client, start(anon_client))
    assert anon_client.get("/api/me").json()["id"] == user.id  # GitHub now signs in here


def test_cant_link_a_github_account_that_has_its_own_account(client, anon_client, fake_github):
    fake_github.emails = [{"email": "ada@work.example", "primary": True, "verified": True}]
    finish(anon_client, start(anon_client))  # someone already signed up with this GitHub account

    response = finish(client, start(client, next=SETTINGS, link=True))
    assert response.headers["location"] == f"{APP}{SETTINGS}&github_error=in_use"
    assert client.get("/api/me").json()["providers"] == ["google"]


def test_linking_github_needs_the_web_app_session(anon_client, fake_github):
    response = anon_client.get(
        "/api/auth/github/link", params={"next": SETTINGS}, follow_redirects=False
    )
    assert response.headers["location"] == f"{APP}{SETTINGS}&github_error=failed"
    assert "bb_github_state" not in response.cookies


def test_signing_out_while_on_github_doesnt_link(client, fake_github):
    state = start(client, next=SETTINGS, link=True)
    client.cookies.delete(SESSION_COOKIE)

    response = finish(client, state)
    assert response.headers["location"] == f"{APP}{SETTINGS}&github_error=failed"
    assert SESSION_COOKIE not in response.cookies


def test_linking_google_to_an_account_made_with_github(anon_client, fake_github, monkeypatch):
    finish(anon_client, start(anon_client))
    google_says(monkeypatch, sub="google-ada", email="ada@gmail.example")

    me = anon_client.post("/api/auth/google/link", json={"credential": "token"}).json()
    assert me["providers"] == ["google", "github"]
    assert me["email"] == "ada@example.com"


def test_cant_link_a_google_account_that_has_its_own_account(
    anon_client, fake_github, monkeypatch, user
):
    fake_github.emails = [{"email": "ada@work.example", "primary": True, "verified": True}]
    finish(anon_client, start(anon_client))
    google_says(monkeypatch, sub=user.google_sub, email=user.email)

    response = anon_client.post("/api/auth/google/link", json={"credential": "token"})
    assert response.status_code == 409
    assert anon_client.get("/api/me").json()["providers"] == ["github"]


def test_unlinking(client, anon_client, fake_github, user):
    fake_github.emails = [{"email": "ada@work.example", "primary": True, "verified": True}]
    finish(client, start(client, next=SETTINGS, link=True))

    assert client.delete("/api/auth/github/link").json()["providers"] == ["google"]
    # That GitHub account (another email) no longer opens this account.
    finish(anon_client, start(anon_client))
    assert anon_client.get("/api/me").json()["id"] != user.id


def test_cant_unlink_the_only_way_to_sign_in(client):
    assert client.delete("/api/auth/google/link").status_code == 409
    assert client.get("/api/me").json()["providers"] == ["google"]


def test_linking_and_unlinking_only_from_the_web_app(client, anon_client, monkeypatch):
    token = client.post("/api/tokens", json={}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    google_says(monkeypatch, sub="google-other", email="other@example.com")

    response = anon_client.post(
        "/api/auth/google/link", json={"credential": "token"}, headers=headers
    )
    assert response.status_code == 401
    assert anon_client.delete("/api/auth/google/link", headers=headers).status_code == 401
