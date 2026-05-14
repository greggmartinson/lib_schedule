from __future__ import annotations

from pathlib import Path

import streamlit as st

from library_schedule.condense import build_condensed_summary
from library_schedule.config import load_config
from library_schedule.debug import save_fetch_debug_artifacts
from library_schedule.fetcher import (
    AuthRequiredError,
    BrowserLaunchError,
    fetch_schedule_pages,
)
from library_schedule.ics_calendar import (
    fetch_calendar_agenda_bundle,
)
from library_schedule.parser import ParseError, parse_schedule_pages
from library_schedule.report import (
    render_calendar_agenda_fragment,
    render_html_report,
    render_summary_table_fragment,
)
from library_schedule.transform import trim_summary_rows


CONFIG_PATH = Path("config/settings.yaml")


def main() -> None:
    st.set_page_config(page_title="Library Space Schedule", layout="wide")
    st.title("Library Space Usage Summary")
    st.caption("One-click daily snapshot for display screens and printing.")

    if not CONFIG_PATH.exists():
        st.error("Missing config/settings.yaml. Copy config/settings.example.yaml to start.")
        return

    config = load_config(CONFIG_PATH)

    left, right = st.columns([2, 1])
    refresh_clicked = left.button("Refresh Today's Summary", type="primary", use_container_width=True)
    right.write("")
    right.write("")
    if right.button("How to Re-Login", use_container_width=True):
        st.info("Run: python3 login_once.py")

    if not refresh_clicked:
        st.write("Press **Refresh Today's Summary** to load the latest schedule.")
        return

    with st.spinner("Fetching schedule..."):
        try:
            fetched_pages = fetch_schedule_pages(config)
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
        except AuthRequiredError as exc:
            st.error(str(exc))
            st.code("python3 login_once.py")
            return
        except BrowserLaunchError as exc:
            st.error(str(exc))
            st.code(".venv/bin/playwright install chromium")
            return
        except ParseError as exc:
            st.error(str(exc))
            st.warning(
                "Tip: set `schedule_table_selector` in config/settings.yaml "
                "to a CSS selector for the exact table."
            )
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {exc}")
            return

    debug_dir = save_fetch_debug_artifacts(fetched_pages)
    resolved_url = fetched_pages[0].final_url if fetched_pages else config.schedule_url
    hidden_booking_count = _count_booked_slots(raw_summary) - _count_booked_slots(summary)
    if len(fetched_pages) == 1 and fetched_pages[0].room_name is None:
        st.warning("Room navigation was not detected. The app fell back to single-page parsing.")
    st.caption(f"Fetched {len(fetched_pages)} schedule page(s). Debug saved to `{debug_dir}`.")
    if hidden_booking_count > 0:
        st.warning(
            f"{hidden_booking_count} booked time slot(s) are hidden by the current "
            "top/bottom row trimming settings in config/settings.yaml."
        )

    rows = []
    for period in summary.periods:
        row = {"Period/Time": period.period_label}
        for space in summary.spaces:
            row[space] = period.by_space.get(space, "") or "Open"
        rows.append(row)

    condensed = build_condensed_summary(summary)
    calendar_agenda = None
    if config.ics_calendars:
        calendar_agenda, calendar_warnings = fetch_calendar_agenda_bundle(
            config.ics_calendars,
            summary.report_date,
        )
        for warning in calendar_warnings:
            st.warning(warning)

    st.success(f"Loaded from {resolved_url}")
    st.markdown(
        render_summary_table_fragment(condensed, include_styles=True),
        unsafe_allow_html=True,
    )
    if calendar_agenda is not None:
        st.markdown(
            render_calendar_agenda_fragment(calendar_agenda, include_styles=True),
            unsafe_allow_html=True,
        )
    with st.expander("Detailed slot-by-slot view"):
        st.dataframe(rows, use_container_width=True, hide_index=True)

    report_html = render_html_report(summary, calendar_agenda=calendar_agenda)
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"daily_schedule_{summary.report_date.isoformat()}.html"
    output_path.write_text(report_html, encoding="utf-8")

    st.download_button(
        label="Download Printable HTML",
        data=report_html,
        file_name=output_path.name,
        mime="text/html",
        use_container_width=True,
    )
    st.caption(f"Saved latest report to `{output_path}`")


def _count_booked_slots(summary) -> int:
    return sum(
        1
        for period in summary.periods
        for value in period.by_space.values()
        if value.strip()
    )


if __name__ == "__main__":
    main()
