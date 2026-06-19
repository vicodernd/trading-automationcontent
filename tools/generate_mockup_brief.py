#!/usr/bin/env python3
"""
Generate a per-slide/per-frame mockup brief for the design team.
Usage: python tools/generate_mockup_brief.py "Gravestone Doji candle" single 1
        python tools/generate_mockup_brief.py "5 candlestick patterns" carousel 6
Output: JSON list printed to stdout
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

from tools.utils import parse_json, strip_dashes

load_dotenv()

PROMPT = """You are a content designer briefing a graphic design team for a financial education brand.

Topic: {topic}
Format: {format} ({num_slides} slide(s))

Do NOT use dashes (hyphens - or em dashes —) anywhere in the output. Use commas, periods, or restructure sentences instead.

Generate a design brief for each slide/frame. Each entry must have:
- slide_number: integer starting at 1
- headline: short, bold text (max 8 words)
- body_text: 1-3 sentences of educational content for this slide
- cta: call-to-action text (e.g., "Save this", "Follow for more", "Swipe to learn") — only on last slide
- visual_notes: brief description of what the visual/graphic should show (for the designer)

For a single image: one entry with slide_number = 1.
For carousel: one entry per slide, building a logical narrative arc.

Respond with ONLY valid JSON — a list of objects:
[
  {{
    "slide_number": 1,
    "headline": "...",
    "body_text": "...",
    "cta": "..." or "",
    "visual_notes": "..."
  }}
]"""


def generate_mockup_brief(topic: str, fmt: str, num_slides: int) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(topic=topic, format=fmt, num_slides=num_slides),
            }
        ],
    )

    return strip_dashes(parse_json(message.content[0].text))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python tools/generate_mockup_brief.py <topic> <format> <num_slides>",
            file=sys.stderr,
        )
        sys.exit(1)

    result = generate_mockup_brief(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    print(json.dumps(result, indent=2))
