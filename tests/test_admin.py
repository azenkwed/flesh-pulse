"""Smoke tests for the admin dashboard (separate FastAPI app on port 8081)."""
import base64
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.database.models import Article, User
from backend.auth.utils import hash_password
from datetime import datetime, timezone


def _basic_auth(password: str = "adminpass") -> dict:
    token = base64.b64encode(f"admin:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest_asyncio.fixture
async def admin_client(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    mock_scheduler = MagicMock()
    mock_scheduler.start = MagicMock()
    mock_scheduler.shutdown = MagicMock()

    with patch.dict(os.environ, {"ADMIN_PASSWORD": "adminpass"}), \
         patch("backend.database.db.init_db", new_callable=AsyncMock), \
         patch("backend.scheduler.create_scheduler", return_value=mock_scheduler):
        from admin.app import app as admin_app
        from backend.database.db import get_db
        admin_app.dependency_overrides[get_db] = _override_get_db
        async with AsyncClient(
            transport=ASGITransport(app=admin_app),
            base_url="http://testadmin",
            follow_redirects=False,
        ) as ac:
            yield ac
        admin_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

async def test_admin_dashboard_requires_auth(admin_client):
    resp = await admin_client.get("/")
    assert resp.status_code == 401


async def test_admin_dashboard_wrong_password(admin_client):
    resp = await admin_client.get("/", headers=_basic_auth("wrongpass"))
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

async def test_admin_dashboard_loads(admin_client):
    resp = await admin_client.get("/", headers=_basic_auth())
    assert resp.status_code == 200
    assert b"Sex Health News" in resp.content or b"Admin" in resp.content or b"Dashboard" in resp.content


async def test_admin_articles_list(admin_client):
    resp = await admin_client.get("/articles", headers=_basic_auth())
    assert resp.status_code == 200


async def test_admin_logs(admin_client):
    resp = await admin_client.get("/logs", headers=_basic_auth())
    assert resp.status_code == 200


async def test_admin_users_list(admin_client):
    resp = await admin_client.get("/users", headers=_basic_auth())
    assert resp.status_code == 200


async def test_admin_curation_records(admin_client):
    resp = await admin_client.get("/curation-records", headers=_basic_auth())
    assert resp.status_code == 200


async def test_admin_settings(admin_client):
    resp = await admin_client.get("/settings", headers=_basic_auth())
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Article CRUD
# ---------------------------------------------------------------------------

async def test_admin_article_detail(admin_client, engine):
    # Insert an article into the test DB
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        article = Article(
            url="https://example.com/admin-test",
            title="Admin Test Article",
            description="Test",
            content="",
            source_name="Test",
            source_country="US",
            author="",
            published_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc),
            relevance_score=0.8,
            category="Sexual Health & Education",
            severity="medium",
            tags=[],
            ai_summary="Summary",
            featured=False,
        )
        session.add(article)
        await session.commit()
        await session.refresh(article)
        article_id = article.id

    resp = await admin_client.get(f"/articles/{article_id}", headers=_basic_auth())
    assert resp.status_code == 200
    assert b"Admin Test Article" in resp.content


async def test_admin_article_not_found(admin_client):
    resp = await admin_client.get("/articles/99999", headers=_basic_auth())
    assert resp.status_code == 404


async def test_admin_newsletter_preview(admin_client):
    resp = await admin_client.get("/newsletter-preview", headers=_basic_auth())
    assert resp.status_code == 200
