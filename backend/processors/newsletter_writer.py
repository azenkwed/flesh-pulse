"""Uses Claude Haiku to write a newsletter subject line and intro paragraph."""
import asyncio
import json
import os
import sys

import anthropic
import httpx

_SYSTEM = (
    "You are the editorial voice of Sex Health News, an independent news archive documenting "
    "surveillance, censorship, authoritarian governance, and corporate control. "
    "Write in a clear, serious, and urgent tone."
)

_PROMPT = """Write a newsletter digest header for Sex Health News readers covering {period}'s top stories.

Articles:
{articles}

Respond with JSON only — no markdown fences:
{{
  "subject": "<compelling email subject line, 8-60 chars>",
  "intro": "<2-3 sentence editorial paragraph contextualising these stories>"
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
