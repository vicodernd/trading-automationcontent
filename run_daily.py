#!/usr/bin/env python3
"""
Daily entry point invoked by the OS scheduler at 8 AM.

Flow:
  1. Check the On/Off toggle (automation.state). If Off -> do nothing.
  2. Look up today's topic in materi/Materi Konten.xlsx.
     No row for today, or empty Materi -> do nothing.
  3. Otherwise run the full content-creation workflow for that topic.

Run manually any time with: python run_daily.py
"""

import os
import sys
from datetime import date
from pathlib import Path

# Make every relative path used by the existing tools (.env, credentials.json,
# token.json, the Excel sheet) resolve regardless of how the scheduler launched
# us (launchd sets WorkingDirectory, cron uses `cd`, but Task Scheduler does not).
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation import is_enabled
from run import run
from tools.get_today_topic import get_today_topic


def main() -> None:
    today = date.today()
    stamp = today.isoformat()

    if not is_enabled():
        print(f"[{stamp}] Automation is OFF. Skipping.")
        return

    topic = get_today_topic(today)
    if not topic:
        print(f"[{stamp}] No content scheduled for today. Skipping.")
        return

    print(f"[{stamp}] Scheduled topic: {topic}")
    run(topic)


if __name__ == "__main__":
    main()
