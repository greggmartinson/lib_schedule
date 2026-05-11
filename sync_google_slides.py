from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from library_schedule.bootstrap import ensure_project_venv

ensure_project_venv(__file__)


def _missing_dependency_message(module_name: str) -> str:
    return (
        f"Missing dependency `{module_name}`.\n"
        "Install project dependencies in `.venv` with:\n"
        "  python3 -m venv .venv\n"
        "  .venv/bin/pip install -r requirements.txt\n"
        "  .venv/bin/playwright install chromium"
    )


try:
    from library_schedule.condense import build_condensed_summary
    from library_schedule.config import load_config
    from library_schedule.debug import save_fetch_debug_artifacts
    from library_schedule.fetcher import AuthRequiredError, fetch_schedule_pages
    from library_schedule.ics_calendar import (
        fetch_calendar_agenda_bundle,
    )
    from library_schedule.google_slides_apps_script import (
        sync_condensed_summary_via_apps_script,
    )
    from library_schedule.google_slides import sync_condensed_summary_to_slide
    from library_schedule.parser import ParseError, parse_schedule_pages
    from library_schedule.printing import print_file, render_html_report_to_pdf
    from library_schedule.report import render_html_report
    from library_schedule.transform import trim_summary_rows
except ModuleNotFoundError as exc:
    if exc.name in {
        "bs4",
        "googleapiclient",
        "google_auth_oauthlib",
        "playwright",
        "yaml",
    }:
        raise SystemExit(_missing_dependency_message(exc.name)) from exc
    raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the daily library schedule and sync it to Google Slides."
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where the HTML report will be written.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode while fetching the schedule.",
    )
    parser.add_argument(
        "--no-open-browser",
        action="store_true",
        help="For Apps Script mode, write the submit page without opening it automatically.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="should_print",
        help="Render today's summary to PDF and send it to the system printer.",
    )
    parser.add_argument(
        "--printer",
        default=None,
        help="Optional macOS printer name to use with `lp`. Defaults to the system default printer.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if config.google_slides is None:
        print("ERROR: config/settings.yaml is missing the `google_slides` section.")
        return 1

    try:
        fetched_pages = fetch_schedule_pages(config, headless=not args.headed)
        raw_summary = parse_schedule_pages(
            pages=fetched_pages,
            target_spaces=config.target_spaces,
            room_aliases=config.room_aliases,
            table_selector=config.schedule_table_selector,
        )
        summary = trim_summary_rows(
            summary=raw_summary,
            drop_first_rows=config.drop_first_period_rows,
            drop_last_rows=config.drop_last_period_rows,
        )
    except (AuthRequiredError, ParseError) as exc:
        print(f"ERROR: {exc}")
        return 1

    condensed = build_condensed_summary(summary)
    calendar_agenda = None
    if config.ics_calendars:
        calendar_agenda, calendar_warnings = fetch_calendar_agenda_bundle(
            config.ics_calendars,
            summary.report_date,
        )
        for warning in calendar_warnings:
            print(f"Warning: {warning}")

    try:
        if config.google_slides.apps_script_web_app_url:
            sync_result = sync_condensed_summary_via_apps_script(
                condensed,
                config.google_slides,
                output_dir=args.output_dir,
                open_browser=not args.no_open_browser,
                calendar_agenda=calendar_agenda,
            )
        else:
            sync_result = sync_condensed_summary_to_slide(
                condensed,
                config.google_slides,
                calendar_agenda=calendar_agenda,
            )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = save_fetch_debug_artifacts(fetched_pages)
    out_path = output_dir / f"daily_schedule_{summary.report_date.isoformat()}.html"
    out_path.write_text(
        render_html_report(summary, calendar_agenda=calendar_agenda),
        encoding="utf-8",
    )

    if config.google_slides.apps_script_web_app_url:
        print("Apps Script submit page ready.")
        print(f"Presentation ID: {sync_result.presentation_id}")
        print(f"Target slide: {sync_result.slide_index}")
        print(f"Submit page: {sync_result.submit_page_path}")
        if sync_result.browser_opened:
            print("Browser opened. If prompted, finish Google sign-in and allow the Apps Script.")
        else:
            print("Browser did not open automatically. Open the submit page above in your logged-in browser.")
    else:
        print(f"Slides updated: {sync_result.title}")
        print(f"Presentation ID: {sync_result.presentation_id}")
        print(f"Updated slide: {sync_result.slide_index}")

    if args.should_print:
        pdf_path = output_dir / f"daily_schedule_{summary.report_date.isoformat()}.pdf"
        try:
            rendered_pdf = render_html_report_to_pdf(out_path, pdf_path)
            print_output = print_file(rendered_pdf, printer_name=args.printer)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"ERROR: printing failed: {exc}")
            return 1

        print(f"Printable PDF: {rendered_pdf}")
        if print_output:
            print(f"Print job: {print_output}")
    print(f"Debug saved: {debug_dir}")
    print(f"Report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
