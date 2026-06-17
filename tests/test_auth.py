"""Tests for registration, login, profile, and saved-article flows."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from backend.database.models import User
from backend.auth.utils import hash_password


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def test_register_page(client):
    resp = await client.get("/register")
    assert resp.status_code == 200
    assert b"Register" in resp.content


async def test_register_success(client):
    with patch("backend.auth.routes.send_verification_email", MagicMock()):
        resp = await client.post("/register", data={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "confirm_password": "securepassword123",
        })
    # Redirect to /login after registration
    assert resp.status_code in (302, 303)


async def test_register_duplicate_email(client, verified_user):
    with patch("backend.auth.routes.send_verification_email", MagicMock()):
        resp = await client.post("/register", data={
            "email": "test@example.com",
            "password": "securepassword123",
            "confirm_password": "securepassword123",
        }, follow_redirects=True)
    # Re-renders registration form with an error
    assert resp.status_code == 200
    assert b"already" in resp.content.lower() or b"registered" in resp.content.lower()


async def test_register_password_mismatch(client):
    with patch("backend.auth.routes.send_verification_email", MagicMock()):
        resp = await client.post("/register", data={
            "email": "mismatch@example.com",
            "password": "password123",
            "confirm_password": "differentpassword",
        }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"match" in resp.content.lower() or b"password" in resp.content.lower()


async def test_register_short_password(client):
    with patch("backend.auth.routes.send_verification_email", MagicMock()):
        resp = await client.post("/register", data={
            "email": "short@example.com",
            "password": "abc",
            "confirm_password": "abc",
        }, follow_redirects=True)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def test_login_page(client):
    resp = await client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in" in resp.content or b"Login" in resp.content


async def test_login_success(client, verified_user):
    resp = await client.post("/login", data={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    assert resp.status_code in (302, 303)
    assert "access_token" in resp.cookies


async def test_login_wrong_password(client, verified_user):
    resp = await client.post("/login", data={
        "email": "test@example.com",
        "password": "wrongpassword",
    }, follow_redirects=True)
    assert resp.status_code == 200
    content_lower = resp.content.lower()
    assert b"invalid" in content_lower or b"incorrect" in content_lower or b"wrong" in content_lower


async def test_login_unknown_email(client):
    resp = await client.post("/login", data={
        "email": "nobody@example.com",
        "password": "anypassword",
    }, follow_redirects=True)
    assert resp.status_code == 200


async def test_login_unverified_user(client, db):
    user = User(
        email="unverified@example.com",
        password_hash=hash_password("password123"),
        email_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()

    resp = await client.post("/login", data={
        "email": "unverified@example.com",
        "password": "password123",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"verif" in resp.content.lower()


async def test_login_rate_limit(client, verified_user):
    """After 10 login attempts from the same IP, the response shows a rate-limit error."""
    import backend.auth.routes as auth_r
    import time
    # Key format is "login:{ip}" — ASGITransport sets host to 127.0.0.1
    auth_r._rl_store["login:127.0.0.1"] = [time.time()] * 10

    resp = await client.post("/login", data={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    # Route returns a rendered 200 with an error message (not a 429)
    assert resp.status_code == 200
    assert b"Too many attempts" in resp.content


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

async def test_logout(auth_client):
    resp = await auth_client.post("/logout")
    assert resp.status_code in (302, 303)
    # Cookie should be cleared
    assert auth_client.cookies.get("access_token") is None or \
           resp.cookies.get("access_token") == ""


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

async def test_profile_requires_auth(client):
    resp = await client.get("/profile")
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers.get("location", "")


async def test_profile_page_loads(auth_client, verified_user):
    resp = await auth_client.get("/profile")
    assert resp.status_code == 200
    assert verified_user.email.encode() in resp.content


async def test_profile_shows_verified_status(auth_client, verified_user):
    resp = await auth_client.get("/profile")
    assert resp.status_code == 200
    assert b"verified" in resp.content.lower()


async def test_profile_update_display_name(auth_client, verified_user):
    resp = await auth_client.post("/profile", data={
        "display_name": "Updated Name",
        "newsletter_frequency": "daily",
    })
    assert resp.status_code in (302, 303)


async def test_profile_update_newsletter_frequency(auth_client, verified_user):
    resp = await auth_client.post("/profile", data={
        "display_name": "",
        "newsletter_frequency": "never",
    })
    assert resp.status_code in (302, 303)


# ---------------------------------------------------------------------------
# Saved articles
# ---------------------------------------------------------------------------

async def test_saved_requires_auth(client):
    resp = await client.get("/saved")
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers.get("location", "")


async def test_saved_empty(auth_client):
    resp = await auth_client.get("/saved")
    assert resp.status_code == 200
    assert b"No saved articles" in resp.content


async def test_saved_with_article(auth_client, sample_article):
    # Save the article via the toggle endpoint
    await auth_client.post(f"/article/{sample_article.id}/save")
    resp = await auth_client.get("/saved")
    assert resp.status_code == 200
    assert sample_article.title.encode() in resp.content


async def test_saved_pagination(auth_client):
    resp = await auth_client.get("/saved?page=1")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

async def test_forgot_password_page(client):
    resp = await client.get("/auth/forgot-password")
    assert resp.status_code == 200


async def test_forgot_password_submit(client, verified_user):
    with patch("backend.auth.routes.send_password_reset_email", MagicMock()):
        resp = await client.post("/auth/forgot-password", data={
            "email": "test@example.com",
        })
    assert resp.status_code in (200, 302, 303)


async def test_forgot_password_unknown_email(client):
    with patch("backend.auth.routes.send_password_reset_email", MagicMock()):
        resp = await client.post("/auth/forgot-password", data={
            "email": "nobody@nowhere.com",
        })
    # Should not reveal whether email exists — same response
    assert resp.status_code in (200, 302, 303)
