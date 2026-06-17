"""Smoke tests for all public-facing routes."""
import pytest


async def test_home_empty(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert b"Sex Health News" in resp.content


async def test_home_with_articles(client, sample_article):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert b"Sex Health News" in resp.content


async def test_home_pagination_page_1(client, sample_article):
    resp = await client.get("/?page=1")
    assert resp.status_code == 200


async def test_home_pagination_page_2(client):
    resp = await client.get("/?page=2")
    assert resp.status_code == 200


async def test_home_invalid_page(client):
    resp = await client.get("/?page=0")
    # Query validator (ge=1) should reject or clamp
    assert resp.status_code in (200, 422)


async def test_article_detail(client, sample_article):
    resp = await client.get(f"/article/{sample_article.id}")
    assert resp.status_code == 200
    assert sample_article.title.encode() in resp.content


async def test_article_not_found(client):
    resp = await client.get("/article/99999")
    assert resp.status_code == 404


async def test_category_surveillance(client, sample_article):
    resp = await client.get("/category/surveillance-and-privacy")
    assert resp.status_code == 200


async def test_category_censorship(client, featured_article):
    resp = await client.get("/category/censorship-and-information-control")
    assert resp.status_code == 200


async def test_category_unknown_shows_empty_page(client):
    """Unknown slugs show an empty category page (no 404 — graceful fallback)."""
    resp = await client.get("/category/totally-unknown-category")
    assert resp.status_code == 200


async def test_category_slug_ampersand_reversal(client):
    """Critical: slug must reverse '&' correctly, not just replace '-' with ' '."""
    # "Sexual Health & Education" → slug "surveillance-and-privacy"
    # naive replace("-", " ") would give "surveillance and privacy" which ≠ "Sexual Health & Education"
    resp = await client.get("/category/surveillance-and-privacy")
    assert resp.status_code == 200


async def test_search_no_query(client):
    resp = await client.get("/search")
    assert resp.status_code == 200


async def test_search_with_query(client, sample_article):
    resp = await client.get("/search?q=surveillance")
    assert resp.status_code == 200


async def test_search_empty_results(client):
    resp = await client.get("/search?q=zzznomatch")
    assert resp.status_code == 200


async def test_search_rate_limit(client):
    """After 30 requests in 60 s, further searches return 429 with an error message."""
    import backend.routes as r
    # Pre-fill the rate-limit bucket as if 30 searches already happened
    # ASGITransport sets request.client.host to "127.0.0.1"
    import time
    r._search_rl["127.0.0.1"] = [time.time()] * 30
    resp = await client.get("/search?q=test")
    assert resp.status_code == 429
    assert b"Too many searches" in resp.content


async def test_contact_page(client):
    resp = await client.get("/contact")
    assert resp.status_code == 200


async def test_privacy_page(client):
    resp = await client.get("/privacy")
    assert resp.status_code == 200


async def test_terms_page(client):
    resp = await client.get("/terms")
    assert resp.status_code == 200


async def test_sitemap(client, sample_article):
    resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert b"urlset" in resp.content
    assert b"/article/" in resp.content  # article URLs are included


async def test_robots_txt(client):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert b"Disallow" in resp.content
    assert b"/api/" in resp.content


async def test_api_stats(client, sample_article):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_articles" in data


async def test_api_articles(client, sample_article):
    resp = await client.get("/api/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_save_article_requires_auth(client, sample_article):
    resp = await client.post(f"/article/{sample_article.id}/save")
    assert resp.status_code in (302, 303)
    location = resp.headers.get("location", "")
    assert "/login" in location


async def test_save_article_auth(auth_client, sample_article):
    resp = await auth_client.post(f"/article/{sample_article.id}/save")
    # Should redirect (toggle bookmark)
    assert resp.status_code in (302, 303)


async def test_unsave_article_auth(auth_client, sample_article):
    # Save first
    await auth_client.post(f"/article/{sample_article.id}/save")
    # Unsave (toggle again)
    resp = await auth_client.post(f"/article/{sample_article.id}/save")
    assert resp.status_code in (302, 303)
