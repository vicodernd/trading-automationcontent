#!/usr/bin/env python3
"""
Compile all content assets into a structured Google Doc for the design team.
Called by run.py — not intended to be run standalone.

On first run, OAuth will open a browser tab. After completing auth, token.json is cached.
Subsequent runs are fully headless.
"""

import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/documents"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")


def _get_creds():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def _append_table(requests, rows):
    """Append a table of rows (list of list of strings) to the batchUpdate requests list."""
    num_rows = len(rows)
    num_cols = len(rows[0]) if rows else 0
    if num_rows == 0 or num_cols == 0:
        return

    requests.append(
        {
            "insertTable": {
                "rows": num_rows,
                "columns": num_cols,
                "endOfSegmentLocation": {"segmentId": ""},
            }
        }
    )


def compile_to_gdocs(topic: str, captions: dict, image_refs: list, mockup_brief: list, fmt: str) -> str:
    creds = _get_creds()
    service = build("docs", "v1", credentials=creds)

    # Create the document
    doc = service.documents().create(body={"title": f"{topic} — Content Brief"}).execute()
    doc_id = doc["documentId"]

    # Build content as plain text with clear structure
    # Google Docs API batchUpdate for tables is complex; we use plain formatted text instead
    lines = []

    # Header
    lines.append(f"{topic} — Content Brief\n")
    lines.append(f"Format: {fmt.upper()}\n\n")

    # Section 1: Captions
    lines.append("SECTION 1: CAPTIONS\n")
    lines.append("─" * 40 + "\n\n")
    lines.append(f"INSTAGRAM\n{captions.get('instagram', '')}\n\n")
    lines.append(f"THREADS\n{captions.get('threads', '')}\n\n")
    lines.append(f"X (TWITTER)\n{captions.get('x', '')}\n\n")

    # Section 2: Image References
    lines.append("SECTION 2: IMAGE REFERENCES\n")
    lines.append("─" * 40 + "\n\n")
    if image_refs:
        for i, ref in enumerate(image_refs, 1):
            lines.append(f"{i}. {ref.get('title', 'Untitled')}\n")
            desc = ref.get("description", "")
            if desc:
                lines.append(f"   Description: {desc}\n")
            lines.append(f"   Image URL: {ref.get('url', '')}\n")
            lines.append(f"   Source: {ref.get('source', '')}\n")
            query = ref.get("search_query", "")
            if query:
                lines.append(f"   Search term: {query}\n")
            lines.append("\n")
    else:
        lines.append("No image references found.\n\n")

    # Section 3: Mockup Brief
    lines.append("SECTION 3: MOCKUP BRIEF\n")
    lines.append("─" * 40 + "\n\n")
    for frame in mockup_brief:
        slide_num = frame.get("slide_number", "?")
        lines.append(f"SLIDE {slide_num}\n")
        lines.append(f"Headline:     {frame.get('headline', '')}\n")
        lines.append(f"Body text:    {frame.get('body_text', '')}\n")
        cta = frame.get("cta", "")
        if cta:
            lines.append(f"CTA:          {cta}\n")
        lines.append(f"Visual notes: {frame.get('visual_notes', '')}\n\n")

    full_text = "".join(lines)

    # Insert the content into the doc
    service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": full_text,
                    }
                }
            ]
        },
    ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return doc_url
