from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
import json
from pathlib import Path
import webbrowser

from .booking_text import clean_booking_for_display
from .config import GoogleSlidesConfig
from .google_slides import extract_presentation_id
from .model import CondensedScheduleSummary


@dataclass(frozen=True)
class AppsScriptSyncResult:
    presentation_id: str
    slide_index: int
    web_app_url: str
    submit_page_path: Path
    browser_opened: bool


def sync_condensed_summary_via_apps_script(
    summary: CondensedScheduleSummary,
    config: GoogleSlidesConfig,
    output_dir: str | Path,
    open_browser: bool = True,
) -> AppsScriptSyncResult:
    web_app_url = (config.apps_script_web_app_url or "").strip()
    if not web_app_url:
        raise ValueError(
            "config/settings.yaml is missing google_slides.apps_script_web_app_url"
        )

    payload = build_apps_script_payload(summary, config)
    submit_page_path = write_apps_script_submit_page(
        payload=payload,
        web_app_url=web_app_url,
        output_path=Path(output_dir) / "google_slides_sync_submit.html",
    )

    browser_opened = False
    if open_browser:
        browser_opened = webbrowser.open(submit_page_path.resolve().as_uri())

    return AppsScriptSyncResult(
        presentation_id=payload["presentationId"],
        slide_index=payload["slideIndex"],
        web_app_url=web_app_url,
        submit_page_path=submit_page_path,
        browser_opened=browser_opened,
    )


def build_apps_script_payload(
    summary: CondensedScheduleSummary,
    config: GoogleSlidesConfig,
) -> dict:
    generated_at = datetime.now()
    return {
        "presentationId": extract_presentation_id(config.presentation_url),
        "slideIndex": config.slide_index,
        "reportDateIso": summary.report_date.isoformat(),
        "reportDateLabel": summary.report_date.strftime("%A, %B %-d, %Y"),
        "generatedAtLabel": generated_at.strftime("Generated %I:%M %p").lstrip("0"),
        "rooms": [
            {
                "name": room_name,
                "entries": [
                    {"booking": clean_booking_for_display(entry.booking), "when": entry.when}
                    for entry in summary.by_space.get(room_name, [])
                ],
            }
            for room_name in summary.spaces
        ],
    }


def write_apps_script_submit_page(
    payload: dict,
    web_app_url: str,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_apps_script_submit_page(payload=payload, web_app_url=web_app_url),
        encoding="utf-8",
    )
    return output_path


def render_apps_script_submit_page(payload: dict, web_app_url: str) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Updating Google Slides…</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f5f7fb;
        color: #243041;
        margin: 0;
        padding: 32px 20px;
      }}
      .card {{
        max-width: 720px;
        margin: 0 auto;
        background: white;
        border: 1px solid #d7dee8;
        border-radius: 14px;
        padding: 24px;
        box-shadow: 0 12px 40px rgba(36, 48, 65, 0.08);
      }}
      h1 {{
        font-size: 24px;
        margin: 0 0 12px;
      }}
      p {{
        margin: 0 0 10px;
        line-height: 1.5;
      }}
      .muted {{
        color: #5e6b7a;
      }}
      button {{
        margin-top: 16px;
        font-size: 15px;
        padding: 10px 14px;
        border-radius: 10px;
        border: 0;
        background: #175cd3;
        color: white;
        cursor: pointer;
      }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Updating Google Slides…</h1>
      <p>This page submits today’s library schedule to your Apps Script web app.</p>
      <p class="muted">If Google asks you to sign in, complete that first. If the update does not start automatically, use the button below.</p>
      <form id="sync-form" method="post" action="{escape(web_app_url, quote=True)}">
        <textarea name="payload" style="display:none">{escape(payload_json)}</textarea>
        <button type="submit">Submit Schedule Update</button>
      </form>
    </div>
    <script>
      window.addEventListener("load", function () {{
        document.getElementById("sync-form").submit();
      }});
    </script>
  </body>
</html>
"""
