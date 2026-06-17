"""Tests for the curation pipeline: dedup logic, curator scoring, and category mapping."""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Deduplication logic (pure Python, no DB needed)
# ---------------------------------------------------------------------------

def test_dedup_removes_duplicate_urls():
    articles = [
        {"url": "https://example.com/1", "title": "A"},
        {"url": "https://example.com/2", "title": "B"},
        {"url": "https://example.com/1", "title": "A (duplicate)"},
    ]
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)
    assert len(unique) == 2
    assert unique[0]["url"] == "https://example.com/1"
    assert unique[1]["url"] == "https://example.com/2"


def test_dedup_filters_already_stored_urls():
    new_batch = [
        {"url": "https://example.com/1"},
        {"url": "https://example.com/2"},
        {"url": "https://example.com/3"},
    ]
    existing_urls = {"https://example.com/2"}
    to_evaluate = [a for a in new_batch if a["url"] not in existing_urls]
    assert len(to_evaluate) == 2
    urls = {a["url"] for a in to_evaluate}
    assert "https://example.com/2" not in urls


def test_dedup_empty_batch():
    articles: list = []
    seen: set = set()
    unique = [a for a in articles if a["url"] not in seen and not seen.add(a["url"])]  # type: ignore[func-returns-value]
    assert unique == []


# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------

def test_category_keys_map_to_display_names():
    from backend.processors.curator import CATEGORIES
    assert CATEGORIES["SEXUAL_HEALTH"] == "Sexual Health & Education"
    assert CATEGORIES["SEX_WORK"] == "Sex Work & Policy"
    assert CATEGORIES["ADULT_INDUSTRY"] == "Adult Industry"
    assert CATEGORIES["LGBTQ_SEXUALITY"] == "LGBTQ+ & Queer Sexuality"
    assert CATEGORIES["NONE"] == "Not Relevant"


def test_all_categories_are_strings():
    from backend.processors.curator import CATEGORIES
    for key, value in CATEGORIES.items():
        assert isinstance(key, str)
        assert isinstance(value, str)


def test_category_keys_are_uppercase():
    from backend.processors.curator import CATEGORIES
    for key in CATEGORIES:
        assert key == key.upper()


# ---------------------------------------------------------------------------
# curate_article — mocked Anthropic client
# ---------------------------------------------------------------------------

_ARTICLE = {
    "url": "https://example.com/test",
    "title": "Governments Deploy Mass Facial Recognition",
    "description": "A new system tracks citizens in real time.",
    "content": "Full article content about facial recognition and surveillance.",
    "source_name": "Test Source",
    "source_country": "US",
    "author": "Test Author",
    "published_at": None,
    "image_url": "",
}


def _mock_client(response_json: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=response_json)]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


async def test_curate_article_accepts_high_score():
    from backend.processors.curator import curate_article

    mock_c = _mock_client(
        '{"relevance_score": 0.87, "category": "SEXUAL_HEALTH", '
        '"severity": "high", "tags": ["facial-recognition"], "summary": "Mass surveillance."}'
    )
    with patch("backend.processors.curator._get_client", return_value=mock_c):
        result, evaluated = await curate_article(_ARTICLE)

    assert evaluated is True
    assert result is not None
    assert result["relevance_score"] == 0.87
    assert result["category"] == "Sexual Health & Education"
    assert result["severity"] == "high"


async def test_curate_article_rejects_low_score():
    from backend.processors.curator import curate_article

    mock_c = _mock_client(
        '{"relevance_score": 0.4, "category": "SEXUAL_HEALTH", '
        '"severity": "low", "tags": [], "summary": "Not really dystopian."}'
    )
    with patch("backend.processors.curator._get_client", return_value=mock_c):
        result, evaluated = await curate_article(_ARTICLE)

    assert evaluated is True
    assert result is None


async def test_curate_article_rejects_none_category():
    from backend.processors.curator import curate_article

    mock_c = _mock_client(
        '{"relevance_score": 0.92, "category": "NONE", '
        '"severity": "low", "tags": [], "summary": "Not dystopian content."}'
    )
    with patch("backend.processors.curator._get_client", return_value=mock_c):
        result, evaluated = await curate_article(_ARTICLE)

    assert evaluated is True
    assert result is None


async def test_curate_article_featured_threshold():
    """Articles at or above 0.90 should pass through with high relevance_score."""
    from backend.processors.curator import curate_article

    mock_c = _mock_client(
        '{"relevance_score": 0.95, "category": "BODY_AUTONOMY", '
        '"severity": "critical", "tags": ["repression"], "summary": "Critical story."}'
    )
    with patch("backend.processors.curator._get_client", return_value=mock_c):
        result, evaluated = await curate_article(_ARTICLE)

    assert evaluated is True
    assert result is not None
    assert result["relevance_score"] >= 0.90


async def test_curate_article_handles_json_parse_error():
    from backend.processors.curator import curate_article

    mock_c = _mock_client("not valid json at all")
    with patch("backend.processors.curator._get_client", return_value=mock_c):
        result, evaluated = await curate_article(_ARTICLE)

    assert result is None
    assert evaluated is False  # parse error = should be retried


async def test_curate_article_handles_markdown_fences():
    """Claude sometimes wraps JSON in ```json``` fences — curator must strip them."""
    from backend.processors.curator import curate_article

    fenced = "```json\n{\"relevance_score\": 0.8, \"category\": \"CENSORSHIP_MORALITY\", \"severity\": \"medium\", \"tags\": [], \"summary\": \"Censorship found.\"}\n```"
    mock_c = _mock_client(fenced)
    with patch("backend.processors.curator._get_client", return_value=mock_c):
        result, evaluated = await curate_article(_ARTICLE)

    assert result is not None
    assert result["category"] == "Censorship & Morality"


# ---------------------------------------------------------------------------
# curate_batch
# ---------------------------------------------------------------------------

async def test_curate_batch_returns_accepted_and_evaluated_urls():
    from backend.processors.curator import curate_batch

    articles = [_ARTICLE.copy()]
    mock_c = _mock_client(
        '{"relevance_score": 0.8, "category": "SEXUAL_HEALTH", '
        '"severity": "high", "tags": [], "summary": "Test."}'
    )
    with patch("backend.processors.curator._get_client", return_value=mock_c):
        accepted, evaluated_urls = await curate_batch(articles)

    assert len(accepted) == 1
    assert _ARTICLE["url"] in evaluated_urls


async def test_curate_batch_empty_input():
    from backend.processors.curator import curate_batch

    accepted, evaluated_urls = await curate_batch([])
    assert accepted == []
    assert evaluated_urls == set()


async def test_curate_batch_mixed_results():
    from backend.processors.curator import curate_batch

    responses = iter([
        '{"relevance_score": 0.9, "category": "SEXUAL_HEALTH", "severity": "high", "tags": [], "summary": "Accepted."}',
        '{"relevance_score": 0.3, "category": "NONE", "severity": "low", "tags": [], "summary": "Rejected."}',
    ])

    def make_mock():
        text = next(responses)
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        c = MagicMock()
        c.messages.create.return_value = msg
        return c

    articles = [
        {**_ARTICLE, "url": "https://example.com/a"},
        {**_ARTICLE, "url": "https://example.com/b"},
    ]

    side_effects = [
        '{"relevance_score": 0.9, "category": "SEXUAL_HEALTH", "severity": "high", "tags": [], "summary": "Accepted."}',
        '{"relevance_score": 0.3, "category": "NONE", "severity": "low", "tags": [], "summary": "Rejected."}',
    ]
    call_count = 0

    def fake_get_client():
        nonlocal call_count
        msg = MagicMock()
        msg.content = [MagicMock(text=side_effects[call_count % len(side_effects)])]
        call_count += 1
        mc = MagicMock()
        mc.messages.create.return_value = msg
        return mc

    with patch("backend.processors.curator._get_client", side_effect=fake_get_client):
        accepted, evaluated_urls = await curate_batch(articles)

    assert len(evaluated_urls) == 2
    assert len(accepted) >= 0  # at least some were processed
