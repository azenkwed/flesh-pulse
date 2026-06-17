"""NewsAPI collector — fetches articles using sexuality/health keywords."""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from backend.processors.content_cleaner import strip_boilerplate

BASE_URL = "https://newsapi.org/v2/everything"

SEARCH_QUERIES = [
    "sexual health policy",
    "sex education legislation",
    "sex work decriminalization",
    "FOSTA SESTA sex work",
    "adult industry regulation",
    "pornography censorship law",
    "age verification online adult",
    "LGBTQ sexuality rights",
    "reproductive rights abortion",
    "body autonomy legislation",
    "consent law sexual assault",
    "sex therapy research",
    "sexually transmitted infection STI",
    "OnlyFans adult content platform",
    "obscenity law morality",
]


async def collect_all() -> list[dict[str, Any]]:
    newsapi_key = os.getenv("NEWSAPI_KEY", "")
    if not newsapi_key:
        print("[NewsAPI] No API key set — skipping.")
        return []

    since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    articles: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient(verify=sys.platform != "win32") as client:
        for query in SEARCH_QUERIES:
            try:
                resp = await client.get(
                    BASE_URL,
                    params={
                        "q": query,
                        "from": since,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": 10,
                        "apiKey": newsapi_key,
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
                data = resp.json()
                for art in data.get("articles", []):
                    url = art.get("url", "")
                    if not url or url in seen_urls or url == "[Removed]":
                        continue
                    seen_urls.add(url)

                    pub_str = art.get("publishedAt", "")
                    pub_date = None
                    if pub_str:
                        try:
                            pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    source = art.get("source", {})
                    articles.append({
                        "url": url,
                        "title": (art.get("title") or "").strip(),
                        "description": strip_boilerplate(art.get("description") or "")[:2000],
                        "content": strip_boilerplate(art.get("content") or "")[:2000],
                        "source_name": source.get("name", "Unknown"),
                        "source_country": "",
                        "author": art.get("author", ""),
                        "published_at": pub_date,
                        "image_url": art.get("urlToImage", "") or "",
                    })
            except Exception as exc:
                print(f"[NewsAPI] Query '{query}' failed: {exc}")

    return articles
