from app.api import auth as auth_api
from app.auth.security import SESSION_COOKIE, GoogleIdentity


def test_me_requires_auth(anon_client):
    assert anon_client.get("/api/me").status_code == 401


def test_me_with_session_cookie(client, user):
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_invalid_session_cookie(anon_client):
    anon_client.cookies.set(SESSION_COOKIE, "not-a-jwt")
    assert anon_client.get("/api/me").status_code == 401


def test_google_login_creates_user_and_sets_cookie(anon_client, monkeypatch):
    async def fake_verify(credential):
        assert credential == "google-id-token"
        return GoogleIdentity(
            {"sub": "new-sub", "email": "new@example.com", "name": "New", "picture": None}
        )

    # Don't call Google in tests: replace the verifier with a fake.
    monkeypatch.setattr(auth_api, "verify_google_credential", fake_verify)

    response = anon_client.post("/api/auth/google", json={"credential": "google-id-token"})
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"
    assert SESSION_COOKIE in response.cookies

    # Same client now carries the cookie.
    assert anon_client.get("/api/me").json()["email"] == "new@example.com"


def test_google_login_rejects_bad_token(anon_client, monkeypatch):
    async def fake_verify(credential):
        raise ValueError("Wrong audience")

    monkeypatch.setattr(auth_api, "verify_google_credential", fake_verify)
    response = anon_client.post("/api/auth/google", json={"credential": "forged"})
    assert response.status_code == 401


def test_logout_clears_cookie(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    # The server clears the cookie by re-sending it already expired.
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE}=") and "Max-Age=0" in set_cookie


def test_token_lifecycle(client, anon_client):
    created = client.post("/api/tokens", json={"name": "Chrome laptop"})
    assert created.status_code == 201
    token = created.json()["token"]
    assert token.startswith("bb_pat_")

    # Plaintext is only returned once.
    listed = client.get("/api/tokens").json()
    assert len(listed) == 1 and "token" not in listed[0]

    headers = {"Authorization": f"Bearer {token}"}
    me = anon_client.get("/api/me", headers=headers)
    assert me.status_code == 200
    assert client.get("/api/tokens").json()[0]["last_used_at"] is not None

    assert client.delete(f"/api/tokens/{created.json()['id']}").status_code == 204
    assert anon_client.get("/api/me", headers=headers).status_code == 401


def test_cannot_revoke_someone_elses_token(client, client_for, other_user):
    token_id = client.post("/api/tokens", json={}).json()["id"]
    assert client_for(other_user).delete(f"/api/tokens/{token_id}").status_code == 404
