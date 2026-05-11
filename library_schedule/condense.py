from __future__ import annotations

from datetime import datetime

from .model import CondensedScheduleSummary, ScheduleSummary, SummaryEntry


TIME_RANGE_FORMATS = (
    "%I:%M %p - %I:%M %p",
    "%I %p - %I %p",
)


def build_condensed_summary(summary: ScheduleSummary) -> CondensedScheduleSummary:
    by_space: dict[str, list[SummaryEntry]] = {}
    for space in summary.spaces:
        by_space[space] = _summarize_space(summary, space)

    return CondensedScheduleSummary(
        report_date=summary.report_date,
        spaces=summary.spaces,
        by_space=by_space,
    )


def _summarize_space(summary: ScheduleSummary, space: str) -> list[SummaryEntry]:
    entries: list[SummaryEntry] = []
    active_booking = ""
    start_label = ""
    end_label = ""

    for period in summary.periods:
        booking = period.by_space.get(space, "").strip()
        if booking == active_booking:
            if booking:
                end_label = period.period_label
            continue

        if active_booking:
            entries.append(
                SummaryEntry(
                    booking=active_booking,
                    when=_format_label_range(start_label, end_label),
                )
            )

        active_booking = booking
        start_label = period.period_label
        end_label = period.period_label

    if active_booking:
        entries.append(
            SummaryEntry(
                booking=active_booking,
                when=_format_label_range(start_label, end_label),
            )
        )

    return entries


def _format_label_range(start_label: str, end_label: str) -> str:
    start_range = _parse_time_range(start_label)
    end_range = _parse_time_range(end_label)
    if start_range and end_range:
        start_text = _format_clock(start_range[0])
        end_text = _format_clock(end_range[1])
        return f"{start_text} - {end_text}"

    if start_label == end_label:
        return start_label
    return f"{start_label} to {end_label}"


def _parse_time_range(label: str) -> tuple[datetime, datetime] | None:
    cleaned = " ".join(label.split())
    for fmt in TIME_RANGE_FORMATS:
        try:
            start_text, end_text = cleaned.split(" - ", maxsplit=1)
        except ValueError:
            return None
        try:
            start_dt = datetime.strptime(start_text, fmt.split(" - ")[0])
            end_dt = datetime.strptime(end_text, fmt.split(" - ")[1])
        except ValueError:
            continue
        return start_dt, end_dt
    return None


def _format_clock(value: datetime) -> str:
    text = value.strftime("%I:%M %p")
    if text.startswith("0"):
        text = text[1:]
    if text.endswith(":00 AM") or text.endswith(":00 PM"):
        text = text.replace(":00 ", " ")
    return text
