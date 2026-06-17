"""Uses Claude Haiku to write a newsletter subject line and intro paragraph."""
import asyncio
import json
import os
import sys

import anthropic
import httpx

_SYSTEM = (
    "You are the editorial voice of Sex Health News, an independent news platform covering sexual health, "
    "reproductive rights, and wellness for people who want facts they can trust.\n\n"
    "Your readers are 18-35, informed, and expect clarity without stigma or judgment. "
    "Write in a conversational, direct tone — like you're explaining something important to a friend. "
    "Be honest about complexity, don't oversimplify, and lead with what matters most.\n\n"
    "Avoid: Corporate speak, unnecessary jargon, preachy language, false urgency. "
    "Embrace: Real language, practical context, nuanced take, actual impact."
)

_PROMPT = """Write a newsletter digest for Sex Health News readers covering {period}'s top stories.

Articles:
{articles}

Create a subject line that makes people actually want to open this email (not spammy, just honest).
Then write 2-3 sentences that contextualize these stories and explain why they matter right now.

Respond with JSON only — no markdown fences:
{{
  "subject": "<subject line that gets opened: 8-60 chars, no clickbait>",
  "intro": "<2-3 sentences: plain language, real context, why this matters to readers>"
}}"""


def _call_sync(articles: list[dict], frequency: str) -> dict:
    period = "today" if frequency == "daily" else "this week"
    lines = [
        f"{i}. [{a['category']}] {a['title']} ({a['source_name']})"
        for i, a in enumerate(articles, 1)
    ]
    prompt = _PROMPT.format(period=period, articles="\n".join(lines))

    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        http_client=httpx.Client(verify=sys.platform != "win32"),
    )
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip().rstrip("```").strip()
    return json.loads(text)


async def write_newsletter(articles: list[dict], frequency: str) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_sync, articles, frequency)
