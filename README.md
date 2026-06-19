# Content Automation

Automated social media content creation built on the WAT framework (Workflows, Agents, Tools). Give it a trading or financial topic and it generates platform captions, sources image references, decides the content format, builds a mockup brief, and compiles everything into a Google Doc for the design team.

It can run on a schedule: every day at 8 AM it reads a schedule spreadsheet, finds today's topic, and produces the brief automatically. If there is no topic for today, it does nothing.

## How the daily trigger works

1. At 8 AM the OS scheduler runs `run_daily.py`.
2. `run_daily.py` checks the On/Off toggle (`automation.state`). If Off, it stops.
3. It reads `materi/Materi Konten.xlsx` and matches today's date in the `Tanggal` column.
4. If a matching row has a `Materi` value, it runs the full workflow for that topic. If the date has no row, or the `Materi` cell is empty, it skips silently.

The scheduler is native to each OS, detected automatically:

| OS      | Mechanism      |
|---------|----------------|
| macOS   | launchd        |
| Windows | Task Scheduler |
| Linux   | cron           |

## Setup

1. **Get the project into your home folder** (not Documents, Desktop, or Downloads)
   ```
   cd ~
   git clone https://github.com/vicodernd/trading-automationcontent.git
   cd trading-automationcontent
   ```
   On macOS this matters: the system blocks scheduled jobs from reading `~/Documents`, `~/Desktop`, and `~/Downloads`. Keeping the project in your home folder avoids that completely, with no settings to change. On Windows and Linux the location does not matter, so this rule is safe everywhere.

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Configure your API key**
   Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY`.

4. **Add Google OAuth credentials**
   Download your OAuth client file from Google Cloud Console and save it as `credentials.json` in the project root. Then run the workflow once manually so a browser opens and you complete sign in:
   ```
   python run.py "test topic"
   ```
   This creates `token.json`. The scheduled 8 AM run is headless and cannot open a browser, so this first manual run is required on every machine.

5. **Fill the schedule sheet**
   Open `materi/Materi Konten.xlsx`. Column `Tanggal` holds the date (a real date value, including the year), column `Materi` holds the topic for that date. One row per day you want content.

6. **Install and enable the daily job**
   ```
   python automation.py install
   python automation.py on
   ```

## Controlling the automation

```
python automation.py install     # register the daily 8 AM job
python automation.py uninstall    # remove it
python automation.py on           # enable (runs at 8 AM)
python automation.py off          # disable (the 8 AM run does nothing)
python automation.py status       # show On/Off state and whether the job is registered
```

Turning it Off does not remove the scheduled job. The job stays registered and simply does nothing until you turn it On again, so toggling never asks for permissions.

## Notes per OS

- **macOS:** `browser-act` (BrowserAct CLI) is optional. If it is missing, image references fall back to Google Images search links.
- **macOS privacy (important):** macOS protects `~/Documents`, `~/Desktop`, and `~/Downloads`. A scheduled launchd job cannot read files there even though a Terminal run works, so the 8 AM run fails with `Operation not permitted`. The easiest fix is the one in step 1: keep the project in your home folder. If you must keep it in a protected folder, grant Full Disk Access to your Python interpreter in System Settings under Privacy and Security. `python automation.py install` warns you when the project sits in a protected folder.
- **Windows:** the scheduled task is named `ContentDaily` and runs with `pythonw.exe` so no console window appears. Logs still go to `.tmp/content-daily.log`.
- **Linux:** the cron line is tagged with the comment `# content-daily` for clean install and uninstall.

## Files

```
automation.py            On/Off toggle + per-OS scheduler install/uninstall
run_daily.py             8 AM entry point (toggle gate -> date lookup -> workflow)
run.py                   Manual one-off run: python run.py "<topic>"
tools/get_today_topic.py Reads the schedule sheet, returns today's topic
tools/                   Generation and compilation tools (captions, refs, format, brief, gdocs)
workflows/               WAT workflow SOPs
materi/Materi Konten.xlsx  The schedule: Tanggal + Materi
```

## Security

Never commit secrets. `.env`, `credentials.json`, and `token.json` are gitignored and must stay that way. Each person who clones this repo supplies their own Anthropic key and their own Google OAuth credentials.
