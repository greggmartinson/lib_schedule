# Library Space Daily Summary

This project creates a single daily view of who is using these spaces:

- MC C220.6
- MC C220.7
- MC C220.9
- MC Center
- MC Lab North
- MC Lab South
- MC Minneapolis
- MC St. Paul

It supports:

- A one-click Streamlit dashboard button (`Refresh Today's Summary`)
- Printable HTML output for display screens and paper
- Optional ICS calendar events on the dashboard, printable report, and slide deck
- One-time login capture, so credentials are not stored in code
- Optional Google Slides sync for a live slide deck

## 1) Setup

```bash
cd /Users/martigre000/Desktop/contract/Library_schedule
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp config/settings.example.yaml config/settings.yaml
```

Update `config/settings.yaml` if you need:

- `schedule_url`
- `schedule_table_selector` (if parser cannot find the right table)
- `drop_first_period_rows` and `drop_last_period_rows` to trim extra rows
- `room_aliases` for any header text variations
- `ics_calendars` settings for today's extra calendar events across one or more room feeds
- `google_slides` settings for the live presentation sync

## 2) One-time login

Run this once, or whenever your login session expires:

```bash
python3 login_once.py
```

If `.venv` exists, the script will automatically rerun itself with `.venv/bin/python`.

A browser opens. Log in normally. The script now waits for the schedule page to come back and saves the session automatically.

## 3) Daily button view

```bash
streamlit run app.py
```

Then click **Refresh Today's Summary**.

The app displays a condensed daily summary table and keeps the detailed slot-by-slot view in an expander. It also writes a printable report to:

- `output/daily_schedule_YYYY-MM-DD.html`
- Raw fetched schedule pages for debugging are saved under `output/debug/`

## Daily Quick Run (No Changes Needed)

### Option A: Dashboard (local web server + button)

```bash
cd /Users/martigre000/Desktop/contract/Library_schedule
source .venv/bin/activate
streamlit run app.py
```

Then click **Refresh Today's Summary** in the browser.

Shortcut: double-click `start_dashboard.command`.

### Option B: No server (just generate/open printable report)

```bash
cd /Users/martigre000/Desktop/contract/Library_schedule
source .venv/bin/activate
python3 generate_report.py
```

Shortcut: double-click `run_daily.command`.

## macOS Automation

You can auto-start the dashboard at login:

1. Open **System Settings** -> **General** -> **Login Items**.
2. Add `/Users/martigre000/Desktop/contract/Library_schedule/start_dashboard.command`.

When you sign in, Streamlit will start locally (`http://localhost:8501`).

## Auto Sync at Login

If you want the daily Google Slides sync sequence to run at login, use:

```bash
/Users/martigre000/Desktop/contract/Library_schedule/login_and_sync.command
```

What it does:

- opens the intranet login browser with `login_once.py`
- waits for you to finish logging in
- saves the auth session automatically
- runs `sync_google_slides.py`
- generates a printable PDF summary for today
- sends that PDF to your default printer

To install it:

1. Open **System Settings** -> **General** -> **Login Items**.
2. Add `/Users/martigre000/Desktop/contract/Library_schedule/login_and_sync.command`.

When you sign in, Terminal will open and run the sequence for you. You will still need to complete the intranet sign-in in the browser window if the session has expired.

If you want to test the same flow manually from Terminal:

```bash
cd /Users/martigre000/Desktop/contract/Library_schedule
source .venv/bin/activate
python3 sync_google_slides.py --print
```

This prints to your default macOS printer. To target a specific printer:

```bash
python3 sync_google_slides.py --print --printer "Your Printer Name"
```

## 4) Command-line report (optional)

```bash
python3 generate_report.py
```

If `.venv` exists, the script will automatically rerun itself with `.venv/bin/python`.

## 5) Google Slides Sync

This project can also rebuild slide 2 of the Google Slides deck in `config/settings.yaml` using your condensed daily summary.
If `ics_calendars` is configured, the same daily run also checks those room feeds for the report date and adds a combined events section to the printable report and the slide deck.
If some rooms are blank, that just means there are no events for those feeds that day.

### Recommended setup: Apps Script with your normal browser login

This is the easiest route if you do not want to use Google Cloud or pay for anything extra.

#### One-time setup in Google Slides

1. Open your presentation in Google Slides.
2. Go to **Extensions** -> **Apps Script**.
3. Delete any starter code in the editor.
4. Open this file on your Mac and paste the whole contents into Apps Script:

```bash
/Users/martigre000/Desktop/contract/Library_schedule/apps_script/google_slides_webapp.gs
```

5. Click **Save**.
6. Click **Deploy** -> **New deployment**.
7. Choose **Web app**.
8. Set:
   - **Execute as**: `Me`
   - **Who has access**: the narrowest option that still includes your logged-in Google account
9. Click **Deploy**.
10. Copy the **Web app URL**.
11. Put that URL into `config/settings.yaml` here:

```yaml
google_slides:
  presentation_url: "https://docs.google.com/presentation/d/12lNrWDhZ95yRpCrf2LoMvkxFhbHJz7WEUAv-asPhgdU/edit?slide=id.g3e7c148e447_1_0#slide=id.g3e7c148e447_1_0"
  slide_index: 2
  apps_script_web_app_url: "PASTE-YOUR-WEB-APP-URL-HERE"
```

If you later change the Apps Script code, update the deployment from **Deploy** -> **Manage deployments** so the live web app uses the new version.

#### Daily run

```bash
cd /Users/martigre000/Desktop/contract/Library_schedule
source .venv/bin/activate
python3 sync_google_slides.py
```

What happens:

- The script fetches the current library schedule
- It builds the condensed summary
- It writes `output/google_slides_sync_submit.html`
- Your default browser opens that local page
- That page submits the summary to your Apps Script using your normal Google browser login
- Slide 2 is rebuilt from the latest summary

Shortcut: double-click `sync_google_slides.command`.

If the browser does not open automatically, open this file in your logged-in browser:

```bash
/Users/martigre000/Desktop/contract/Library_schedule/output/google_slides_sync_submit.html
```

### Optional fallback: Google Slides API

If you prefer the original Google API method, you can still use it.

1. Leave `apps_script_web_app_url` blank in `config/settings.yaml`.
2. Create a Google OAuth desktop-app client.
3. Place the client JSON here:

```bash
/Users/martigre000/Desktop/contract/Library_schedule/config/google_oauth_client_secret.json
```

Then run the same command:

```bash
cd /Users/martigre000/Desktop/contract/Library_schedule
source .venv/bin/activate
python3 sync_google_slides.py
```

The script will:

- Fetch the current library schedule
- Build the condensed daily summary
- Replace slide 2 with a readable room-summary layout
- Save the printable HTML report to `output/`

## Troubleshooting

- If you get `Missing auth session file` or `session appears to be expired`:
  - Run `python3 login_once.py` again.
- If you get `No module named yaml` or another missing package error:
  - Run `.venv/bin/pip install -r requirements.txt`
  - Run `.venv/bin/playwright install chromium`
- If parsing fails:
  - Inspect the schedule page HTML and set `schedule_table_selector` to the exact table selector.
  - Add or adjust `room_aliases` values in `config/settings.yaml`.
- If the Apps Script page says you need permission:
  - Open the web app URL directly in your normal Google browser and finish the Google authorization prompts.
  - Then run `python3 sync_google_slides.py` again.
- If Google Slides API sign-in fails:
  - Confirm `config/google_oauth_client_secret.json` exists.
  - Re-run `python3 sync_google_slides.py` and complete the browser login flow.
