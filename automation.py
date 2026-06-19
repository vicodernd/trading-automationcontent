#!/usr/bin/env python3
"""
Control center for the daily content automation.

Two jobs in one CLI:
  1. Register / remove the 8 AM scheduled job on the native OS scheduler
     (launchd on macOS, Task Scheduler on Windows, cron on Linux).
  2. Toggle the automation On/Off via a tiny state file. The scheduled job
     stays registered either way; the gate decides whether it acts.

Usage:
  python automation.py install     # register the daily 8 AM job
  python automation.py uninstall   # remove it
  python automation.py on          # enable (runs at 8 AM)
  python automation.py off         # disable (8 AM run does nothing)
  python automation.py status      # show On/Off + whether the job is registered
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
STATE_FILE = PROJECT_ROOT / "automation.state"
RUN_DAILY = PROJECT_ROOT / "run_daily.py"
LOG_DIR = PROJECT_ROOT / ".tmp"

# Identifiers used by each OS scheduler so install/uninstall/status agree.
LAUNCHD_LABEL = "com.content.daily"
WINDOWS_TASK = "ContentDaily"
CRON_MARKER = "# content-daily"

HOUR = 8
MINUTE = 0


# ── On/Off state ─────────────────────────────────────────────────────────────

def is_enabled() -> bool:
    """True only if the state file explicitly says 'on'. Missing file -> off."""
    try:
        return STATE_FILE.read_text(encoding="utf-8").strip().lower() == "on"
    except OSError:
        return False


def set_state(on: bool) -> None:
    STATE_FILE.write_text("on" if on else "off", encoding="utf-8")


# ── Interpreter resolution ───────────────────────────────────────────────────

def _python_for_schedule() -> str:
    """Interpreter the scheduled job should run.

    Uses the interpreter that ran this command (so it points at the user's
    venv/system Python). On Windows, prefer pythonw.exe so no console window
    pops up at 8 AM.
    """
    exe = Path(sys.executable)
    if platform.system() == "Windows":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return str(exe)


# ── macOS: launchd ───────────────────────────────────────────────────────────

def _launchd_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def _warn_if_tcc_protected() -> None:
    """macOS protects ~/Documents, ~/Desktop, ~/Downloads (TCC). A launchd job
    cannot read files there unless the interpreter has Full Disk Access, even
    though a Terminal run works. Warn at install time so it is not a silent
    8 AM failure."""
    home = Path.home()
    protected = [home / "Documents", home / "Desktop", home / "Downloads"]
    if any(p == PROJECT_ROOT or p in PROJECT_ROOT.parents for p in protected):
        print("\n  ! macOS note: this project is inside a privacy-protected folder")
        print(f"    ({PROJECT_ROOT}).")
        print("    A scheduled run may fail with 'Operation not permitted'. Fix either:")
        print("      a) System Settings > Privacy & Security > Full Disk Access,")
        print(f"         add your Python interpreter: {sys.executable}")
        print("      b) or move this project outside Documents/Desktop/Downloads")
        print("         (e.g. ~/content-automation) and re-run install.\n")


def _launchd_install() -> None:
    py = _python_for_schedule()
    home_local_bin = str(Path.home() / ".local" / "bin")
    path_value = f"{home_local_bin}:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py}</string>
        <string>{RUN_DAILY}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{PROJECT_ROOT}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{path_value}</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{HOUR}</integer>
        <key>Minute</key>
        <integer>{MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{LOG_DIR / "content-daily.log"}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_DIR / "content-daily.err.log"}</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""
    path = _launchd_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist, encoding="utf-8")

    uid = os.getuid()  # type: ignore[attr-defined]
    # Bootout any stale instance first so re-install picks up changes.
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(path)],
                   capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(path)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        # Older macOS fallback.
        subprocess.run(["launchctl", "load", "-w", str(path)], check=False)
    print(f"Installed launchd job '{LAUNCHD_LABEL}' (daily {HOUR:02d}:{MINUTE:02d}).")
    print(f"  plist: {path}")
    _warn_if_tcc_protected()


def _launchd_uninstall() -> None:
    path = _launchd_plist_path()
    uid = os.getuid()  # type: ignore[attr-defined]
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(path)],
                   capture_output=True)
    if path.exists():
        path.unlink()
    print(f"Removed launchd job '{LAUNCHD_LABEL}'.")


def _launchd_registered() -> bool:
    uid = os.getuid()  # type: ignore[attr-defined]
    result = subprocess.run(["launchctl", "print", f"gui/{uid}/{LAUNCHD_LABEL}"],
                            capture_output=True, text=True)
    return result.returncode == 0


# ── Windows: Task Scheduler ──────────────────────────────────────────────────

def _windows_install() -> None:
    py = _python_for_schedule()
    # Inner command, with its own quoting, becomes the /TR value.
    tr = f'"{py}" "{RUN_DAILY}"'
    cmd = ["schtasks", "/Create", "/SC", "DAILY",
           "/ST", f"{HOUR:02d}:{MINUTE:02d}",
           "/TN", WINDOWS_TASK, "/TR", tr, "/F"]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode == 0:
        print(f"Installed Task Scheduler job '{WINDOWS_TASK}' (daily {HOUR:02d}:{MINUTE:02d}).")
    else:
        print(f"schtasks failed (exit {result.returncode}).", file=sys.stderr)


def _windows_uninstall() -> None:
    cmd = ["schtasks", "/Delete", "/TN", WINDOWS_TASK, "/F"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    print(f"Removed Task Scheduler job '{WINDOWS_TASK}'.")


def _windows_registered() -> bool:
    result = subprocess.run(["schtasks", "/Query", "/TN", WINDOWS_TASK],
                            capture_output=True, text=True)
    return result.returncode == 0


# ── Linux: cron ──────────────────────────────────────────────────────────────

def _read_crontab() -> str:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def _write_crontab(content: str) -> None:
    subprocess.run(["crontab", "-"], input=content, text=True, check=True)


def _cron_lines_without_marker(existing: str) -> list:
    return [ln for ln in existing.splitlines() if CRON_MARKER not in ln]


def _cron_install() -> None:
    py = _python_for_schedule()
    log = LOG_DIR / "content-daily.log"
    job = (f'{MINUTE} {HOUR} * * * cd "{PROJECT_ROOT}" && '
           f'"{py}" run_daily.py >> "{log}" 2>&1 {CRON_MARKER}')
    lines = _cron_lines_without_marker(_read_crontab())
    lines.append(job)
    _write_crontab("\n".join(lines) + "\n")
    print(f"Installed cron job (daily {HOUR:02d}:{MINUTE:02d}).")
    print(f"  {job}")


def _cron_uninstall() -> None:
    lines = _cron_lines_without_marker(_read_crontab())
    _write_crontab(("\n".join(lines) + "\n") if lines else "")
    print("Removed cron job.")


def _cron_registered() -> bool:
    return any(CRON_MARKER in ln for ln in _read_crontab().splitlines())


# ── OS dispatch ──────────────────────────────────────────────────────────────

def _dispatch():
    osname = platform.system()
    if osname == "Darwin":
        return _launchd_install, _launchd_uninstall, _launchd_registered
    if osname == "Windows":
        return _windows_install, _windows_uninstall, _windows_registered
    if osname == "Linux":
        return _cron_install, _cron_uninstall, _cron_registered
    raise SystemExit(f"Unsupported OS: {osname}")


def cmd_install() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    install, _, _ = _dispatch()
    install()
    print("Tip: run 'python automation.py on' to enable it.")


def cmd_uninstall() -> None:
    _, uninstall, _ = _dispatch()
    uninstall()


def cmd_on() -> None:
    set_state(True)
    print("Automation ON. Will run every day at 08:00.")


def cmd_off() -> None:
    set_state(False)
    print("Automation OFF. The 08:00 job will do nothing.")


def cmd_status() -> None:
    _, _, registered = _dispatch()
    state = "ON" if is_enabled() else "OFF"
    job = "registered" if registered() else "NOT registered"
    print(f"OS:        {platform.system()}")
    print(f"Toggle:    {state}   (automation.state)")
    print(f"Scheduler: {job}   (daily 08:00)")
    if not registered():
        print("  -> run 'python automation.py install' to register the 8 AM job.")


COMMANDS = {
    "install": cmd_install,
    "uninstall": cmd_uninstall,
    "on": cmd_on,
    "off": cmd_off,
    "status": cmd_status,
}


def main(argv) -> int:
    if len(argv) != 1 or argv[0] not in COMMANDS:
        print(__doc__)
        print(f"Commands: {', '.join(COMMANDS)}", file=sys.stderr)
        return 1
    COMMANDS[argv[0]]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
