"""AI-powered curation — uses Claude to score and categorize articles."""
import json
import os
import sys
from typing import Any

import anthropic

CATEGORIES = {
    "SEXUAL_HEALTH":           "Sexual Health & Wellness",
    "REPRODUCTIVE_HEALTH":     "Reproductive Health & Policy",
    "MATERNAL_CHILD_HEALTH":   "Maternal & Child Health",
    "INFECTIOUS_DISEASES":     "Infectious Diseases & STIs",
    "MENTAL_HEALTH":           "Mental Health & Sexuality",
    "LGBTQ_RIGHTS":            "LGBTQ+ Rights & Issues",
    "SEX_EDUCATION":           "Sex Education & Literacy",
    "SEXUAL_VIOLENCE":         "Sexual Violence & Consent",
    "SEX_WORKERS_INDUSTRY":    "Sex Workers & Adult Industry",
    "NONE":                    "Not Relevant",
}

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

SYSTEM_PROMPT = """You are the editorial AI for Sex Health News, an independent news aggregator providing comprehensive reporting on sexual health, reproductive rights, and wellness. Your role is to evaluate news articles and determine whether they are relevant to this editorial mission.

A relevant article covers real events or findings involving:
- Sexual health & wellness: sexual function, satisfaction, menstrual health, fertility, PCOS, endometriosis, sexual health research
- Reproductive health & policy: abortion access, contraception regulation, family planning laws, reproductive medicine
- Maternal & child health: pregnancy care, childbirth, postpartum care, maternal mortality, child sexual health education
- Infectious diseases & STIs: HIV/AIDS, STI testing and treatment, viral infections, prevention strategies
- Mental health & sexuality: body image, anxiety, depression, sexual dysfunction, relationships, sexual psychology
- LGBTQ+ rights & issues: legal rights, discrimination, same-sex marriage, trans healthcare, gender identity
- Sex education & literacy: school curriculum, public awareness campaigns, misinformation debunking
- Sexual violence & consent: assault, harassment, survivor support, consent education
- Sex workers & adult industry: sex work legalization, labor protections, content creators, industry safety

HARD REJECT — score 0.0 regardless of other factors:
- Any content involving minors in a sexual context
- Generic politics, crime, or business news with no sexual health, rights, or wellness angle
- Celebrity gossip with no substantive health, rights, or educational dimension

Evaluate each article and respond with JSON only — no explanation, no markdown."""

EVAL_PROMPT = """Evaluate this news article for relevance to Sex Health News.

Title: {title}
Source: {source}
Description: {description}
Content: {content}

Respond with this exact JSON structure:
{{
  "relevance_score": <float 0.0-1.0, how strongly relevant>,
  "category": <one of: SEXUAL_HEALTH, REPRODUCTIVE_HEALTH, MATERNAL_CHILD_HEALTH, INFECTIOUS_DISEASES, MENTAL_HEALTH, LGBTQ_RIGHTS, SEX_EDUCATION, SEXUAL_VIOLENCE, SEX_WORKERS_INDUSTRY, NONE>,
  "severity": <one of: low, medium, high, critical>,
  "tags": [<up to 5 short descriptive tags>],
  "summary": <one sentence: what makes this relevant, or why it does not qualify>
}}"""


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        import httpx
        _client = anthropic.Anthropic(
            api_key=key,
            http_client=httpx.Client(verify=sys.platform != "win32"),
        )
    return _client


async def curate_article(article: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    """
    Returns (enriched article, True) if accepted, (None, True) if evaluated but
    rejected, and (None, False) if evaluation failed and should be retried later.
    """
    min_score = float(os.getenv("MIN_RELEVANCE_SCORE", "0.65"))

    prompt = EVAL_PROMPT.format(
        title=article.get("title", ""),
        source=article.get("source_name", ""),
        description=article.get("description", "")[:800],
        content=article.get("content", "")[:800],
    )

    try:
        client = _get_client()
        import asyncio
        loop = asyncio.get_running_loop()

        def _call():
            return client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

        msg = await loop.run_in_executor(None, _call)
        raw = msg.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[Curator] JSON parse error for '{article.get('title', '')}': {exc}")
        return None, False
    except Exception as exc:
        print(f"[Curator] API error for '{article.get('title', '')}': {exc}")
        return None, False

    score = float(result.get("relevance_score", 0.0))
    category_key = result.get("category", "NONE")

    if score < min_score or category_key == "NONE":
        return None, True

    tags = result.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    return {
        **article,
        "relevance_score": score,
        "category": CATEGORIES.get(category_key, category_key),
        "severity": result.get("severity", "low"),
        "tags": tags,
        "ai_summary": result.get("summary", ""),
    }, True


async def curate_batch(articles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str]]:
    """Curate articles, returning accepted articles and successfully evaluated URLs."""
    import asyncio
    semaphore = asyncio.Semaphore(5)
    error_count = 0

    async def _rate_limited(art):
        nonlocal error_count
        async with semaphore:
            try:
                return await curate_article(art)
            except Exception as exc:
                error_count += 1
                print(f"[Curator] Unexpected error for '{art.get('title', '')}': {exc}")
                return None, False

    tasks = [_rate_limited(art) for art in articles]
    results = await asyncio.gather(*tasks)
    accepted = [result for result, evaluated in results if result is not None]
    evaluated_urls = {
        art["url"]
        for art, (result, evaluated) in zip(articles, results)
        if evaluated
    }
    if error_count:
        print(f"[Curator] {error_count} articles failed due to API errors (not counted as rejections)")
    return accepted, evaluated_urls
