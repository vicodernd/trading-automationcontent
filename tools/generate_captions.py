#!/usr/bin/env python3
"""
Generate social media captions (Instagram, Threads, X) for a given topic.
Usage: python tools/generate_captions.py "Gravestone Doji candle"
Output: JSON printed to stdout
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

from tools.utils import parse_json, strip_dashes

load_dotenv()

PROMPT = """You are a social media copywriter for a financial education brand.
Generate captions for the topic: {topic}

Rules:
- Instagram: visual hook opening, educational body (2-3 sentences), 3-5 relevant hashtags
- Threads: conversational, 1-3 sentences, no hashtags, feels like a smart insight
- X: punchy, under 280 characters total, 1-2 hashtags max, high signal
- Do NOT use dashes (hyphens - or em dashes —) anywhere in the output. Use commas, periods, or restructure the sentence instead.

Respond with ONLY valid JSON in this exact format:
{{
  "instagram": "...",
  "threads": "...",
  "x": "..."
}}"""


def generate_captions(topic: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": PROMPT.format(topic=topic)}],
    )

    return strip_dashes(parse_json(message.content[0].text))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/generate_captions.py <topic>", file=sys.stderr)
        sys.exit(1)

    result = generate_captions(sys.argv[1])
    print(json.dumps(result, indent=2))
