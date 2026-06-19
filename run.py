#!/usr/bin/env python3
"""
Content Creation Automation — WAT Framework
Usage: python run.py "Gravestone Doji candle"

Workflow:
  Step 1 (parallel): generate_captions + search_image_refs + determine_format
  Step 2:            generate_mockup_brief  (needs format from Step 1)
  Step 3:            compile_to_gdocs       (needs all results)
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from tools.compile_to_gdocs import compile_to_gdocs
from tools.determine_format import determine_format
from tools.generate_captions import generate_captions
from tools.generate_mockup_brief import generate_mockup_brief
from tools.search_image_refs import search_image_refs


def run(topic: str):
    print(f"\n[START] Topic: {topic}\n")

    # ── Step 1: Run three tools in parallel ──────────────────────────────────
    print("[Step 1/3] Running in parallel: captions + image refs + format decision...")

    results = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(generate_captions, topic): "captions",
            executor.submit(search_image_refs, topic): "image_refs",
            executor.submit(determine_format, topic): "format_decision",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
                print(f"  ✓ {key} done")
            except Exception as e:
                print(f"  ✗ {key} failed: {e}", file=sys.stderr)
                results[key] = None

    captions = results.get("captions") or {}
    image_refs = results.get("image_refs") or []
    format_decision = results.get("format_decision") or {}

    fmt = format_decision.get("format", "single")
    num_slides = format_decision.get("num_slides", 1)
    reasoning = format_decision.get("reasoning", "")

    print(f"\n  Format: {fmt.upper()} ({num_slides} slide(s))")
    print(f"  Reason: {reasoning}")

    # ── Step 2: Generate mockup brief ────────────────────────────────────────
    print("\n[Step 2/3] Generating mockup brief...")
    try:
        mockup_brief = generate_mockup_brief(topic, fmt, num_slides)
        print(f"  ✓ {len(mockup_brief)} frame(s) generated")
    except Exception as e:
        print(f"  ✗ Mockup brief failed: {e}", file=sys.stderr)
        mockup_brief = []

    # ── Step 3: Compile to Google Docs ───────────────────────────────────────
    print("\n[Step 3/3] Compiling to Google Docs...")
    try:
        doc_url = compile_to_gdocs(topic, captions, image_refs, mockup_brief, fmt)
        print(f"\n[DONE] Google Doc created:")
        print(f"  {doc_url}\n")
    except Exception as e:
        print(f"  ✗ Google Docs compile failed: {e}", file=sys.stderr)
        print("\nPartial results (not compiled to Docs):")
        print("  Captions:", captions)
        print("  Image refs:", len(image_refs), "found")
        print("  Mockup frames:", len(mockup_brief))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py <topic>", file=sys.stderr)
        print('Example: python run.py "Gravestone Doji candle"', file=sys.stderr)
        sys.exit(1)

    run(sys.argv[1])
