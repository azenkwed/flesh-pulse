"""Uses Claude Haiku to write a tweet for a featured article."""
import asyncio
import os
import sys

import anthropic
import httpx

_SYSTEM = (
    "You are the Twitter/X writer for Sex Health News, an independent news publication "
    "tracking surveillance, censorship, and authoritarian control.\n\n"
    "Voice: Direct, factual, urgent. No clickbait. No exclamation points. "
    "No 'You won't believe...' No sycophancy. Write like a journalist breaking a story, "
    "not like a content creator chasing engagement.\n\n"
    "Your audience follows Sex Health News because they want the truth plainly stated."
)

_PROMPT = """Write a single tweet for this article. Under 230 characters (the URL will be appended separately).

Title: {title}
Category: {category}
Severity: {severity}
Source: {source}
Summary: {summary}

Rules:
- State the most important fact plainly
- No exclamation points, no ALL CAPS, no emojis unless the story warrants one
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
