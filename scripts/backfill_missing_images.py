#!/usr/bin/env python3
"""Backfill article images by scraping OG/Twitter metadata from source pages."""
import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.collectors.rss_collector import _extract_page_image  # noqa: E402
from backend.database.db import SessionLocal  # noqa: E402
from backend.database.models import Article  # noqa: E402
from sqlalchemy import select  # noqa: E402


async def main() -> None:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Article).where(Article.image_url.is_(None) | (Article.image_url == ""))
            )
        ).scalars().all()

        if not rows:
            print("No articles need image backfill.")
            return

        print(f"Found {len(rows)} articles missing images.")
        updated = 0
        failed = 0

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; SexHealthNews/1.0; +https://sexhealthnew.com)"},
            verify=False,
        ) as client:
            for article in rows:
                image_url = await _extract_page_image(client, article.url)
                if not image_url:
                    failed += 1
                    print(f"[MISS] {article.id} {article.source_name}: {article.title[:80]}")
                    continue

                article.image_url = image_url
                updated += 1
                print(f"[OK]   {article.id} {article.source_name}: {article.title[:80]}")

            await session.commit()

    print(f"Updated {updated} articles, skipped {failed}.")


if __name__ == "__main__":
    asyncio.run(main())
