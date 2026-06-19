#!/usr/bin/env python3
"""
Image references for a topic — Claude-generated descriptions with Google Images search links.

Pipeline:
  1. Claude proposes N visual references (title + description) + ONE disambiguated search query
  2. Each reference gets a clickable Google Images search link for that query

Usage: python -m tools.search_image_refs "Gravestone Doji candle" [num_results]
Output: JSON list printed to stdout
"""

import os
import sys
import urllib.parse

import anthropic
from dotenv import load_dotenv

from tools.utils import parse_json

load_dotenv()

DEFAULT_NUM_RESULTS = 5

PROMPT = """You are an art director for a financial education brand.
For the topic: {topic}

Do two things:
1. Propose {num} distinct visual references the design team should look for. Each has:
   - title: short label (max 8 words)
   - description: 1-2 sentences describing the visual (composition, what it shows, style)
2. Write ONE precise image-search query ("search_query") that will surface the RIGHT images.
   Disambiguate jargon — e.g. for "Gravestone Doji candle" use trading terms like
   "gravestone doji candlestick chart pattern trading" so it does not return cemetery photos.

Respond with ONLY valid JSON:
{{
  "search_query": "...",
  "references": [
    {{ "title": "...", "description": "..." }}
  ]
}}"""


def search_image_refs(topic: str, num_results: int = DEFAULT_NUM_RESULTS) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1536,
        messages=[
            {"role": "user", "content": PROMPT.format(topic=topic, num=num_results)}
        ],
    )

    data = parse_json(message.content[0].text)
    refs = data.get("references", [])
    search_query = data.get("search_query", topic)

    google_link = "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(search_query)

    for ref in refs:
        ref["url"] = google_link
        ref["source"] = "Google Images search"
        ref["search_query"] = search_query

    return refs


if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: python -m tools.search_image_refs <topic> [num_results]", file=sys.stderr)
        sys.exit(1)

    topic = sys.argv[1]
    num = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_NUM_RESULTS

    result = search_image_refs(topic, num)
    print(json.dumps(result, indent=2))
