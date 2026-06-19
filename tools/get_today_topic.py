#!/usr/bin/env python3
"""
Look up the content topic scheduled for a given date in the schedule sheet.

Reads `materi/Materi Konten.xlsx` (columns: Tanggal, Materi) and returns the
Materi for today's date, or None when there is no matching row or the Materi
cell is empty.

Usage: python -m tools.get_today_topic
Output: prints the topic to stdout if found, otherwise prints nothing.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHEET = PROJECT_ROOT / "materi" / "Materi Konten.xlsx"

# Excel's day-zero. Using 1899-12-30 (not 12-31) correctly accounts for Excel's
# fictional 1900 leap year, for any date after 1900-03-01.
_EXCEL_EPOCH = datetime(1899, 12, 30)


def _coerce_date(value) -> Optional[date]:
    """Normalize a Tanggal cell value into a datetime.date, or None if unparseable."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        # Excel serial date number.
        return (_EXCEL_EPOCH + timedelta(days=float(value))).date()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # ISO first, then common day-first formats used in Indonesian sheets.
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def get_today_topic(today: Optional[date] = None,
                    sheet_path: Optional[Path] = None) -> Optional[str]:
    """Return the Materi scheduled for `today`, or None if none / empty.

    `today` defaults to the local current date.
    `sheet_path` defaults to materi/Materi Konten.xlsx under the project root.
    """
    if today is None:
        today = date.today()
    sheet_path = Path(sheet_path) if sheet_path else DEFAULT_SHEET

    if not sheet_path.exists():
        print(f"[get_today_topic] Schedule sheet not found: {sheet_path}", file=sys.stderr)
        return None

    wb = openpyxl.load_workbook(sheet_path, data_only=True, read_only=True)
    try:
        ws = wb.active
        for idx, row in enumerate(ws.iter_rows(values_only=True)):
            if idx == 0:  # header row
                continue
            if not row:
                continue
            tanggal = row[0] if len(row) > 0 else None
            materi = row[1] if len(row) > 1 else None
            if _coerce_date(tanggal) == today:
                if materi is not None and str(materi).strip():
                    return str(materi).strip()
                return None  # date scheduled but Materi empty -> skip
        return None
    finally:
        wb.close()


if __name__ == "__main__":
    topic = get_today_topic()
    if topic:
        print(topic)
    sys.exit(0)
