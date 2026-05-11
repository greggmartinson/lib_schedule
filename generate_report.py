from __future__ import annotations

import argparse
from pathlib import Path

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
    from library_schedule.config import load_config
    from library_schedule.debug import save_fetch_debug_artifacts
    from library_schedule.fetcher import AuthRequiredError, fetch_schedule_pages
    from library_schedule.ics_calendar import (
        fetch_calendar_agenda_bundle,
    )
    from library_schedule.parser import ParseError, parse_schedule_pages
    from library_schedule.report import render_html_report
    from library_schedule.transform import trim_summary_rows
except ModuleNotFoundError as exc:
    if exc.name in {"bs4", "playwright", "yaml"}:
        raise SystemExit(_missing_dependency_message(exc.name)) from exc
    raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate daily summary for library spaces."
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
        help="Run browser in headed mode for debugging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

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

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    calendar_agenda = None
    if config.ics_calendars:
        calendar_agenda, calendar_warnings = fetch_calendar_agenda_bundle(
            config.ics_calendars,
            summary.report_date,
        )
        for warning in calendar_warnings:
            print(f"Warning: {warning}")

    debug_dir = save_fetch_debug_artifacts(fetched_pages)
    out_path = output_dir / f"daily_schedule_{summary.report_date.isoformat()}.html"
    out_path.write_text(
        render_html_report(summary, calendar_agenda=calendar_agenda),
        encoding="utf-8",
    )

    hidden_booking_count = _count_booked_slots(raw_summary) - _count_booked_slots(summary)
    resolved_url = fetched_pages[0].final_url if fetched_pages else config.schedule_url
    print(f"Resolved URL: {resolved_url}")
    print(f"Fetched pages: {len(fetched_pages)}")
    print(f"Debug saved: {debug_dir}")
    print(f"Report written: {out_path}")
    if hidden_booking_count > 0:
        print(
            "Warning: "
            f"{hidden_booking_count} booked time slot(s) were hidden by the current "
            "row trimming settings."
        )
    if len(fetched_pages) == 1 and fetched_pages[0].room_name is None:
        print("Warning: room navigation was not detected; single-page fallback parsing was used.")
    return 0


def _count_booked_slots(summary) -> int:
    return sum(
        1
        for period in summary.periods
        for value in period.by_space.values()
        if value.strip()
    )


if __name__ == "__main__":
    raise SystemExit(main())
