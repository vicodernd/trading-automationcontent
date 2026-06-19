# Workflow: Social Media Content Creation

## Objective
Automate end-to-end content creation for a given trading/financial topic — generating platform captions, sourcing image references, deciding content format, building a mockup brief, and compiling everything into a structured Google Doc for the design team.

## Inputs
- `topic` (string) — the content topic, e.g., `"Gravestone Doji candle"`

## Required Environment Variables
- `ANTHROPIC_API_KEY` — Claude API key (used by all generation tools, including image references)
- `credentials.json` — Google OAuth credentials file (for Docs API, gitignored)

## Required CLI Tools
- `browser-act` — BrowserAct CLI, used to scrape real image URLs from Bing Images.
  Install: `uv tool install browser-act-cli --python 3.12` (binary lands in `~/.local/bin`).
  If absent, image references degrade gracefully to Google Images search links.

> Note: `GOOGLE_API_KEY` / `GOOGLE_CSE_ID` are NO LONGER required (Google Custom Search API was
> abandoned — see "Image references" below). The keys may still sit in `.env` unused.

## Tool Sequence

### Step 1: Run in parallel (all three only need the topic)
| Tool | Input | Output |
|------|-------|--------|
| `tools/generate_captions.py` | topic | JSON: `{ instagram, threads, x }` |
| `tools/search_image_refs.py` | topic | JSON list: `[{ title, description, url, source, search_query }]` (url = real Bing image, or Google search link on fallback) |
| `tools/determine_format.py` | topic | JSON: `{ format, num_slides, reasoning }` |

### Step 2: Generate mockup brief (needs format from Step 1)
| Tool | Input | Output |
|------|-------|--------|
| `tools/generate_mockup_brief.py` | topic, format, num_slides | JSON list of frame objects |

### Step 3: Compile to Google Docs (needs all results)
| Tool | Input | Output |
|------|-------|--------|
| `tools/compile_to_gdocs.py` | topic, captions, image_refs, mockup_brief, format | Google Doc URL |

## Outputs
A Google Doc titled `[topic] — Content Brief` with three sections:
1. **Captions** — Instagram / Threads / X
2. **Image References** — # | Title | Description | Image URL | Source | Search term
3. **Mockup Brief** — Slide # | Headline | Body | CTA | Visual Notes

## Edge Cases & Notes

### Caption generation
- Instagram: visual, hook-first opening, 3–5 relevant hashtags
- Threads: conversational tone, max 3 sentences, no hashtags needed
- X: punchy, under 280 chars, 1–2 hashtags max

### Format decision logic (Claude decides)
- **Single image**: topic is a single concept, one pattern, one indicator
- **Carousel**: topic involves steps, comparisons, lists, or multiple concepts
- `num_slides` for single = 1; for carousel = typically 5–8

### Image references (Claude + BrowserAct scraping Bing Images)
Pipeline inside `search_image_refs.py`:
1. Claude proposes N visual references (title + description) AND one **disambiguated** Bing query.
   Disambiguation matters: "Gravestone Doji" alone returns cemetery photos, so Claude appends
   trading terms (e.g. "...candlestick chart pattern bearish reversal technical analysis trading").
2. `browser-act stealth-extract` scrapes the Bing Images results page (HTML); real full-res URLs are
   parsed from the embedded `murl&quot;:&quot;<url>` JSON blobs.
3. Each reference is paired with a real image URL. `source` = "Bing Images (real image)".
4. **Graceful fallback:** if `browser-act` is missing or returns nothing, each ref falls back to a
   clickable Google Images search link; `source` = "Google Images search (fallback)".

- **Why not Google Custom Search API:** it persistently returned `403 "This project does not have the
  access to Custom Search JSON API"` across 3 API keys and 2 projects, even with the API enabled,
  billing added, and the CSE working in its public preview — likely a new-customer/account access
  restriction. BrowserAct + Bing avoids any image API entirely and returns real URLs.
- **Why Bing not Google Images for scraping:** Google Images obfuscates full-res URLs (base64/JS);
  Bing embeds clean `murl` URLs that parse reliably.
- **Trade-off:** browser scraping adds ~10-30s latency vs the instant Google-link fallback.

### Google Docs compilation
- First run: OAuth will open a browser tab to authenticate — complete it once, token is cached in `token.json`
- If `token.json` exists and is valid, subsequent runs are fully headless
- Doc is always created fresh (not appended to an existing doc)

## Running the Full Workflow
```bash
python run.py "Gravestone Doji candle"
```

## Daily Trigger & On/Off

The workflow can run automatically every day at 8 AM, driven by the schedule sheet `materi/Materi Konten.xlsx` (columns: `Tanggal`, `Materi`).

**Flow:** the OS scheduler runs `run_daily.py`, which (1) checks the On/Off toggle in `automation.state` and stops if Off; (2) reads the sheet, matches today's date against `Tanggal`; (3) runs the workflow for that day's `Materi`. If today has no row, or the `Materi` cell is empty, it skips silently and makes no API call.

**Scheduler is native and auto-detected** by `automation.py`:
- macOS → launchd (`com.vixlify.content-daily`)
- Windows → Task Scheduler (`VixlifyContentDaily`, runs `pythonw.exe`)
- Linux → cron (tagged `# vixlify-content-daily`)

**Commands:**
```bash
python automation.py install     # register the daily 8 AM job (once)
python automation.py on          # enable
python automation.py off         # disable (job stays registered, does nothing)
python automation.py status      # show On/Off + whether the job is registered
python automation.py uninstall   # remove the job
```

**Notes & constraints:**
- The toggle never re-registers the OS job, so On/Off is instant and needs no permissions after install.
- `run_daily.py` chdir's to the project root, so relative paths (`.env`, `credentials.json`, `token.json`, the sheet) resolve regardless of how the scheduler launches it.
- OAuth must be completed once manually (`token.json` present) before scheduling, because the 8 AM run is headless and cannot open a browser.
- `Tanggal` cells must be real date values (with year). openpyxl returns them as `datetime`; serial-number and `dd/mm/yyyy` string forms are also parsed by `tools/get_today_topic.py`.
- The Excel file must be closed (not locked by Excel) at 8 AM for openpyxl to read it.
- Logs for each scheduled run go to `.tmp/content-daily.log` (and `.err.log` on macOS).
- **macOS TCC gotcha:** if the project is under `~/Documents`, `~/Desktop`, or `~/Downloads`, the launchd run fails with `Operation not permitted` (a Terminal run still works). Grant Full Disk Access to the Python interpreter, or move the project outside those folders. `automation.py install` warns when this applies.

## Known Constraints
- Claude API: rate limits apply per tier (used by captions, image refs, format, mockup brief)
- Google Docs API: requires OAuth, not service account (personal workspace)
- BrowserAct/Bing scraping depends on Bing's HTML structure (`murl` JSON); if Bing changes markup,
  parsing may break and the tool falls back to Google Images links
- Image URLs point to third-party sites and may go stale over time — they are design references,
  not guaranteed permanent embeds
