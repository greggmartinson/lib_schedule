from __future__ import annotations

from .model import PeriodRecord, ScheduleSummary


def trim_summary_rows(
    summary: ScheduleSummary,
    drop_first_rows: int = 0,
    drop_last_rows: int = 0,
) -> ScheduleSummary:
    start = max(0, drop_first_rows)
    end_trim = max(0, drop_last_rows)

    periods: list[PeriodRecord] = summary.periods
    if start >= len(periods):
        trimmed: list[PeriodRecord] = []
    elif end_trim == 0:
        trimmed = periods[start:]
    else:
        stop = len(periods) - end_trim
        if stop <= start:
            trimmed = []
        else:
            trimmed = periods[start:stop]

    return ScheduleSummary(
        report_date=summary.report_date,
        spaces=summary.spaces,
        periods=trimmed,
    )
