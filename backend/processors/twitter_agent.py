"""Uses Claude Haiku to write a tweet for a featured article."""
import asyncio
import os
import sys

import anthropic
import httpx

_SYSTEM = (
    "You are the Twitter/X voice of Sex Health News, an independent news platform on sexual health, "
    "reproductive rights, and wellness.\n\n"
    "Your audience: 18-35 year olds who expect honesty without judgment, facts without spin, "
    "and actual relevance to their lives.\n\n"
    "Voice: Conversational, direct, real. State the fact that matters. Use plain language. "
    "When appropriate, acknowledge complexity. Show why this story is worth their attention.\n\n"
    "Avoid: Exclamation points, ALL CAPS, clickbait, corporate-speak, preachy tone, "
    "false urgency, emojis unless the story genuinely warrants one. "
    "Do: Lead with facts, be specific, make the impact clear, keep it human."
)

_PROMPT = """Write a single tweet for this article. Under 230 characters (the URL will be appended separately).

Title: {title}
Category: {category}
Severity: {severity}
Source: {source}
Summary: {summary}

Rules:
- Lead with the fact that actually matters
- Write like you're telling someone why they should care about this
- No exclamation points, no ALL CAPS, avoid emojis (unless genuinely appropriate)
- Keep it human and conversational
- End with 1-2 relevant hashtags
- Do not include a URL (it will be appended automatically)
- Return only the tweet text, nothing else"""


def _call_sync(article: dict) -> str:
    prompt = _PROMPT.format(
        title=article.get("title", ""),
        category=article.get("category", ""),
        severity=article.get("severity", ""),
        source=article.get("source_name", ""),
        summary=article.get("ai_summary") or article.get("description", ""),
    )
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        http_client=httpx.Client(verify=sys.platform != "win32"),
    )
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


async def write_tweet(article: dict) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_sync, article)
