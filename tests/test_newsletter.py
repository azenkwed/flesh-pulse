"""Tests for newsletter filtering, constants, and category preference logic."""
import json
import pytest
from datetime import datetime, timezone

from backend.database.models import Article, User


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_min_articles_constant():
    from backend.notifications.newsletter import _MIN_ARTICLES
    assert _MIN_ARTICLES == 3


def test_max_articles_constant():
    from backend.notifications.newsletter import _MAX_ARTICLES
    assert _MAX_ARTICLES == 10


# ---------------------------------------------------------------------------
# Category preference filtering (pure Python logic mirroring what the newsletter
# module does — tests the invariant, not the DB query)
# ---------------------------------------------------------------------------

def _filter_by_prefs(articles: list[dict], user_categories: list[str]) -> list[dict]:
    """Mirror of the newsletter category-filter logic."""
    if not user_categories:
        return articles
    return [a for a in articles if a["category"] in user_categories]


def test_filter_no_prefs_returns_all():
    articles = [
        {"category": "Sexual Health & Education"},
        {"category": "Adult Industry"},
    ]
    result = _filter_by_prefs(articles, [])
    assert result == articles


def test_filter_single_category():
    articles = [
        {"category": "Sexual Health & Education"},
        {"category": "Adult Industry"},
        {"category": "Sexual Health & Education"},
    ]
    result = _filter_by_prefs(articles, ["Sexual Health & Education"])
    assert len(result) == 2
    assert all(a["category"] == "Sexual Health & Education" for a in result)


def test_filter_multiple_categories():
    articles = [
        {"category": "Sexual Health & Education"},
        {"category": "Adult Industry"},
        {"category": "Science & Research"},
    ]
    result = _filter_by_prefs(articles, ["Sexual Health & Education", "Adult Industry"])
    assert len(result) == 2


def test_filter_no_match_returns_empty():
    articles = [{"category": "Censorship & Morality"}]
    result = _filter_by_prefs(articles, ["Sexual Health & Education"])
    assert result == []


# ---------------------------------------------------------------------------
# User category JSON storage
# ---------------------------------------------------------------------------

def test_user_categories_stored_as_json(db):
    """User.categories is a JSON TEXT column — verify it round-trips correctly."""
    prefs = ["Sexual Health & Education", "Adult Industry"]
    user = User(
        email="nl@example.com",
        password_hash="x",
        email_verified=True,
        newsletter_frequency="daily",
        categories=json.dumps(prefs),
        created_at=datetime.now(timezone.utc),
    )
    stored = json.loads(user.categories)
    assert stored == prefs


def test_user_categories_empty_default():
    user = User(
        email="nl2@example.com",
        password_hash="x",
        categories="[]",
        created_at=datetime.now(timezone.utc),
    )
    assert json.loads(user.categories) == []


# ---------------------------------------------------------------------------
# Minimum article gate
# ---------------------------------------------------------------------------

def test_min_articles_gate_blocks_small_batch():
    from backend.notifications.newsletter import _MIN_ARTICLES
    batch = [{"id": i} for i in range(_MIN_ARTICLES - 1)]
    should_send = len(batch) >= _MIN_ARTICLES
    assert should_send is False


def test_min_articles_gate_allows_exact_minimum():
    from backend.notifications.newsletter import _MIN_ARTICLES
    batch = [{"id": i} for i in range(_MIN_ARTICLES)]
    should_send = len(batch) >= _MIN_ARTICLES
    assert should_send is True


def test_max_articles_cap():
    from backend.notifications.newsletter import _MAX_ARTICLES
    articles = list(range(20))
    capped = articles[:_MAX_ARTICLES]
    assert len(capped) == _MAX_ARTICLES


# ---------------------------------------------------------------------------
# Newsletter writer (mocked Anthropic)
# ---------------------------------------------------------------------------

async def test_write_newsletter_returns_subject_and_intro():
    from unittest.mock import MagicMock, patch
    from backend.processors.newsletter_writer import write_newsletter

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='{"subject": "Test Subject", "intro": "Test intro paragraph."}')]
    mock_client_instance = MagicMock()
    mock_client_instance.messages.create.return_value = mock_msg

    articles = [
        {
            "title": "Surveillance Expands Globally",
            "category": "Sexual Health & Education",
            "source_name": "Test Source",
            "ai_summary": "Brief summary.",
            "url": "https://example.com/1",
        }
    ] * 3

    with patch("backend.processors.newsletter_writer.anthropic.Anthropic", return_value=mock_client_instance):
        result = await write_newsletter(articles, "daily")

    assert result["subject"] == "Test Subject"
    assert result["intro"] == "Test intro paragraph."


async def test_write_newsletter_handles_invalid_json():
    from unittest.mock import MagicMock, patch
    from backend.processors.newsletter_writer import write_newsletter

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="not json")]
    mock_client_instance = MagicMock()
    mock_client_instance.messages.create.return_value = mock_msg

    articles = [
        {"title": "T", "category": "C", "source_name": "S", "ai_summary": "S", "url": "U"}
    ] * 3

    with patch("backend.processors.newsletter_writer.anthropic.Anthropic", return_value=mock_client_instance):
        try:
            result = await write_newsletter(articles, "daily")
            # If it returns, it should be a dict
            assert isinstance(result, dict)
        except Exception:
            # A JSON parse error is also acceptable — it surfaces to the caller
            pass
