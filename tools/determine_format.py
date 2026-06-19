#!/usr/bin/env python3
"""
Use Claude AI to decide whether a topic should be single image or carousel.
Usage: python tools/determine_format.py "Gravestone Doji candle"
Output: JSON printed to stdout
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

from tools.utils import parse_json

load_dotenv()

PROMPT = """You are a social media content strategist for a financial education brand.

Given this content topic: {topic}

Decide whether it should be a SINGLE IMAGE post or a CAROUSEL post.

Rules:
- Single image: one clear concept, one visual, no steps needed (e.g., "What is X")
- Carousel: multiple concepts, steps, comparisons, lists, or deep dives (e.g., "5 types of X", "How X works step by step")
- For single: num_slides = 1
- For carousel: num_slides = 5 to 8 (pick the right number for full coverage without padding)

Respond with ONLY valid JSON in this exact format:
{{
  "format": "single" or "carousel",
  "num_slides": <integer>,
  "reasoning": "<one sentence explaining why>"
}}"""


def determine_format(topic: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": PROMPT.format(topic=topic)}],
    )

    return parse_json(message.content[0].text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/determine_format.py <topic>", file=sys.stderr)
        sys.exit(1)

    result = determine_format(sys.argv[1])
    print(json.dumps(result, indent=2))
