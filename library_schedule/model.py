from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FetchedSchedulePage:
    room_name: str | None
    html: str
    final_url: str


@dataclass(frozen=True)
class PeriodRecord:
    period_label: str
    by_space: dict[str, str]


@dataclass(frozen=True)
class ScheduleSummary:
    report_date: date
    spaces: list[str]
    periods: list[PeriodRecord]


@dataclass(frozen=True)
class SummaryEntry:
    booking: str
    when: str


@dataclass(frozen=True)
class CondensedScheduleSummary:
    report_date: date
    spaces: list[str]
    by_space: dict[str, list[SummaryEntry]]
