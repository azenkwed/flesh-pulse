"""RSS feed collector — pulls from curated sexuality/health sources."""
import asyncio
import json
import sys
import warnings
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from backend.processors.content_cleaner import strip_boilerplate

warnings.filterwarnings("ignore", message=".*SSL.*")

RSS_FEEDS = [
    # Adult industry trade
    {"url": "https://xbiz.com/feed/news", "country": "US", "name": "XBIZ"},
    {"url": "https://avn.com/business/articles/feed", "country": "US", "name": "AVN"},

    # Sexual health & policy
    {"url": "https://rewirenewsgroup.com/feed/", "country": "US", "name": "Rewire News Group"},
    {"url": "https://siecus.org/feed/", "country": "US", "name": "SIECUS"},
    {"url": "https://www.plannedparenthood.org/about-us/newsroom/feed", "country": "US", "name": "Planned Parenthood"},

    # LGBTQ+ & queer
    {"url": "https://www.advocate.com/rss.xml", "country": "US", "name": "The Advocate"},
    {"url": "https://glaad.org/feed/", "country": "US", "name": "GLAAD"},
    {"url": "https://www.pinknews.co.uk/feed/", "country": "UK", "name": "PinkNews"},

    # Science & research
    {"url": "https://theconversation.com/us/topics/sex-7/articles.atom", "country": "INT", "name": "The Conversation: Sex"},
    {"url": "https://www.psychologytoday.com/us/taxonomy/term/61261/feed", "country": "US", "name": "Psychology Today: Sexuality"},

    # Censorship & digital rights
    {"url": "https://www.eff.org/rss/updates.xml", "country": "US", "name": "EFF"},

    # Broad coverage with strong sexuality signal
    {"url": "https://www.theguardian.com/lifeandstyle/sex/rss", "country": "UK", "name": "Guardian: Sex"},
    {"url": "https://feeds.bbci.co.uk/news/health/rss.xml", "country": "UK", "name": "BBC Health"},

    # Google News RSS — keyword-targeted, no API key needed
    {"url": "https://news.google.com/rss/search?q=sexual+health+policy&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: Sexual Health"},
    {"url": "https://news.google.com/rss/search?q=sex+work+decriminalization&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: Sex Work"},
    {"url": "https://news.google.com/rss/search?q=adult+industry+regulation&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: Adult Industry"},
    {"url": "https://news.google.com/rss/search?q=porn+censorship+legislation&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: Porn Legislation"},
    {"url": "https://news.google.com/rss/search?q=LGBTQ+sexuality+rights&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: LGBTQ Sexuality"},
    {"url": "https://news.google.com/rss/search?q=reproductive+rights+abortion&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: Reproductive Rights"},
    {"url": "https://news.google.com/rss/search?q=age+verification+online+pornography&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: Age Verification"},
    {"url": "https://news.google.com/rss/search?q=sexual+consent+law&hl=en&gl=US&ceid=US:en", "country": "INT", "name": "Google News: Consent Law"},
]


async def fetch_feed(client: httpx.AsyncClient, feed_config: dict[str, str]) -> list[dict[str, Any]]:
    articles = []
    try:
        resp = await client.get(feed_config["url"], timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
        for entry in parsed.entries[:20]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

            # Skip articles older than 7 days — some feeds include evergreen/archival content
            if pub_date and (datetime.now(timezone.utc) - pub_date) > timedelta(days=7):
                continue

            url = entry.get("link", "")
            if not url:
                continue

            image_url = _extract_image(entry)
            if not image_url:
                image_url = await _extract_page_image(client, url)

            articles.append({
                "url": url,
                "title": entry.get("title", "").strip(),
                "description": _strip_html(entry.get("summary", "")),
                "content": _strip_html(entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""),
                "source_name": feed_config["name"],
                "source_country": feed_config["country"],
                "author": entry.get("author", ""),
                "published_at": pub_date,
                "image_url": image_url,
            })
    except Exception as exc:
        print(f"[RSS] Failed {feed_config['name']}: {exc}")
    return articles


async def collect_all() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; SexHealthNews/1.0; +https://sexhealthnew.com)"},
        verify=sys.platform != "win32",
    ) as client:
        tasks = [fetch_feed(client, feed) for feed in RSS_FEEDS]
        results = await asyncio.gather(*tasks)
    all_articles = [art for batch in results for art in batch]
    # Deduplicate by URL
    seen: set[str] = set()
    unique = []
    for art in all_articles:
        if art["url"] not in seen:
            seen.add(art["url"])
            unique.append(art)
    return unique


def _strip_html(text: str) -> str:
    if not text:
        return ""
    plain = BeautifulSoup(text, "lxml").get_text(separator="\n").strip()
    return strip_boilerplate(plain)[:2000]


def _extract_image(entry) -> str:
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "media_content") and entry.media_content:
        return entry.media_content[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href", "")
    return ""


_IMAGE_SIZE_CAP = 50_000  # 50 KB is enough to find <head> meta tags


async def _extract_page_image(client: httpx.AsyncClient, url: str) -> str:
    try:
        async with client.stream("GET", url, timeout=10.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            async for chunk in resp.aiter_bytes(4096):
                chunks.append(chunk)
                total += len(chunk)
                if total >= _IMAGE_SIZE_CAP:
                    break
            base_url = str(resp.url)
            raw = b"".join(chunks)
    except Exception:
        return ""

    soup = BeautifulSoup(raw, "lxml")

    meta_keys = [
        ("meta", {"property": "og:image"}, "content"),
        ("meta", {"property": "og:image:secure_url"}, "content"),
        ("meta", {"name": "twitter:image"}, "content"),
        ("meta", {"name": "twitter:image:src"}, "content"),
        ("meta", {"itemprop": "image"}, "content"),
    ]
    for tag_name, attrs, attr_name in meta_keys:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get(attr_name):
            return urljoin(base_url, tag.get(attr_name))

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        ld_raw = (script.string or script.get_text() or "").strip()
        if not ld_raw:
            continue
        try:
            data = json.loads(ld_raw)
        except Exception:
            continue
        image = _find_jsonld_image(data)
        if image:
            return urljoin(base_url, image)

    dom_image = _extract_dom_image(soup, base_url)
    if dom_image:
        return dom_image

    return ""


def _find_jsonld_image(data: Any) -> str:
    if isinstance(data, dict):
        image = data.get("image")
        if isinstance(image, str):
            return image
        if isinstance(image, list) and image:
            first = image[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict) and first.get("url"):
                return first["url"]

        for key in ("@graph", "mainEntity", "primaryImageOfPage", "thumbnailUrl"):
            value = data.get(key)
            found = _find_jsonld_image(value)
            if found:
                return found

        for value in data.values():
            found = _find_jsonld_image(value)
            if found:
                return found

    if isinstance(data, list):
        for item in data:
            found = _find_jsonld_image(item)
            if found:
                return found

    if isinstance(data, str) and data.startswith("http"):
        return data

    return ""


def _extract_dom_image(soup, base_url: str) -> str:
    roots = []
    article = soup.find("article")
    if article:
        roots.append(article)
    main = soup.find("main")
    if main and main is not article:
        roots.append(main)
    roots.append(soup)

    skip_terms = ("logo", "icon", "avatar", "sprite", "button", "banner", "ad", "promo", "share")

    for root in roots:
        for img in root.find_all("img"):
            candidate = _tag_image_url(img)
            if not candidate:
                continue
            lower = candidate.lower()
            alt_text = (img.get("alt") or "").lower()
            class_text = " ".join(img.get("class") or []).lower()
            if any(term in lower or term in alt_text or term in class_text for term in skip_terms):
                continue

            width = _tag_dimension(img.get("width"))
            height = _tag_dimension(img.get("height"))
            if width and height and (width < 200 or height < 120):
                continue

            return urljoin(base_url, candidate)

    return ""


def _tag_image_url(img) -> str:
    for key in (
        "data-src",
        "data-lazy-src",
        "data-original",
        "data-url",
        "src",
    ):
        value = img.get(key)
        if value:
            return value
    return ""


def _tag_dimension(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0
