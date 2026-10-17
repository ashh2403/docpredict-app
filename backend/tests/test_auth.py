from __future__ import annotations

import sqlite3

import jwt

from app.config import settings

from .conftest import PASSWORD, auth_headers, register


def test_register_returns_token_and_hashes_password(client, db_path):
    data = register(client, email="Alice@Example.com")
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"  # normalised
    assert data["user"]["theme"] == "system"
    assert "password" not in str(data["user"]).lower()

    stored = sqlite3.connect(db_path).execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored != PASSWORD and stored.startswith("$2")  # bcrypt


def test_register_duplicate_email_rejected(client):
    register(client)
    res = client.post("/api/auth/register",
                      json={"email": "ALICE@example.com", "full_name": "Other", "password": PASSWORD})
    assert res.status_code == 409


def test_register_validation(client):
    weak = client.post("/api/auth/register", json={"email": "a@example.com", "full_name": "A", "password": "short"})
    assert weak.status_code == 422
    assert "at least 8" in weak.json()["detail"]
    assert "short" not in weak.text  # submitted password is not echoed back

    no_digit = client.post("/api/auth/register",
                           json={"email": "a@example.com", "full_name": "A", "password": "onlyletters"})
    assert no_digit.status_code == 422

    bad_email = client.post("/api/auth/register",
                            json={"email": "not-an-email", "full_name": "A", "password": PASSWORD})
    assert bad_email.status_code == 422

    blank_name = client.post("/api/auth/register",
                             json={"email": "a@example.com", "full_name": "   ", "password": PASSWORD})
    assert blank_name.status_code == 422


def test_login_success_and_failure(client):
    register(client)
    ok = client.post("/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert ok.json()["user"]["full_name"] == "Alice Smith"

    wrong = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "Wrong12345"})
    assert wrong.status_code == 401
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]  # no account enumeration


def test_login_throttled_after_repeated_failures(client):
    register(client)
    for _ in range(5):
        assert client.post("/api/auth/login",
                           json={"email": "alice@example.com", "password": "Wrong12345"}).status_code == 401
    blocked = client.post("/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    assert blocked.status_code == 429


def test_protected_endpoints_require_token(client):
    for method, url in [("get", "/api/users/me"), ("get", "/api/analyses"), ("get", "/api/analyses/stats"),
                        ("get", "/api/analyses/1"), ("delete", "/api/analyses/1"), ("get", "/api/model"),
                        ("post", "/api/auth/logout")]:
        assert getattr(client, method)(url).status_code == 401, url


def test_invalid_and_forged_tokens_rejected(client, alice):
    assert client.get("/api/users/me", headers=auth_headers("garbage")).status_code == 401
    forged = jwt.encode({"sub": str(alice["user"]["id"]), "jti": "x", "exp": 9999999999, "type": "access"},
                        "a-different-secret-key-that-is-long-enough!!", algorithm="HS256")
    assert client.get("/api/users/me", headers=auth_headers(forged)).status_code == 401
    expired = jwt.encode({"sub": str(alice["user"]["id"]), "jti": "y", "exp": 1, "type": "access"},
                         settings.secret_key, algorithm="HS256")
    res = client.get("/api/users/me", headers=auth_headers(expired))
    assert res.status_code == 401 and "expired" in res.json()["detail"].lower()


def test_logout_revokes_token(client, alice):
    assert client.get("/api/users/me", headers=alice["headers"]).status_code == 200
    assert client.post("/api/auth/logout", headers=alice["headers"]).status_code == 200
    assert client.get("/api/users/me", headers=alice["headers"]).status_code == 401
    # A fresh login still works.
    assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD}).status_code == 200


def test_profile_and_theme_update(client, alice):
    res = client.patch("/api/users/me", headers=alice["headers"], json={"full_name": "  Alice   Cooper ", "theme": "dark"})
    assert res.status_code == 200
    assert res.json()["full_name"] == "Alice Cooper"
    assert res.json()["theme"] == "dark"
    assert client.get("/api/users/me", headers=alice["headers"]).json()["theme"] == "dark"
    assert client.patch("/api/users/me", headers=alice["headers"], json={"theme": "neon"}).status_code == 422


def test_change_password(client, alice):
    bad = client.post("/api/users/me/password", headers=alice["headers"],
                      json={"current_password": "Wrong12345", "new_password": "NewPass123"})
    assert bad.status_code == 400
    ok = client.post("/api/users/me/password", headers=alice["headers"],
                     json={"current_password": PASSWORD, "new_password": "NewPass123"})
    assert ok.status_code == 200
    assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": "NewPass123"}).status_code == 200


def test_delete_account_requires_password_and_removes_user(client, alice, db_path):
    assert client.request("DELETE", "/api/users/me", headers=alice["headers"],
                          json={"password": "Wrong12345"}).status_code == 400
    assert client.request("DELETE", "/api/users/me", headers=alice["headers"],
                          json={"password": PASSWORD}).status_code == 200
    assert client.get("/api/users/me", headers=alice["headers"]).status_code == 401
    assert sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["model_loaded"] is True
