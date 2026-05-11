from __future__ import annotations

import unittest
from datetime import date

from library_schedule.condense import build_condensed_summary
from library_schedule.model import PeriodRecord, ScheduleSummary


class CondenseTests(unittest.TestCase):
    def test_merges_adjacent_time_slots(self) -> None:
        summary = ScheduleSummary(
            report_date=date(2026, 5, 5),
            spaces=["MC C220.6", "MC C220.7"],
            periods=[
                PeriodRecord(
                    "9:00 AM - 9:30 AM",
                    {"MC C220.6": "Sam Albert", "MC C220.7": ""},
                ),
                PeriodRecord(
                    "9:30 AM - 10:00 AM",
                    {"MC C220.6": "Sam Albert", "MC C220.7": ""},
                ),
                PeriodRecord(
                    "10:00 AM - 10:30 AM",
                    {"MC C220.6": "Sam Albert", "MC C220.7": ""},
                ),
            ],
        )

        condensed = build_condensed_summary(summary)

        self.assertEqual(len(condensed.by_space["MC C220.6"]), 1)
        self.assertEqual(condensed.by_space["MC C220.6"][0].booking, "Sam Albert")
        self.assertEqual(condensed.by_space["MC C220.6"][0].when, "9 AM - 10:30 AM")
        self.assertEqual(condensed.by_space["MC C220.7"], [])

    def test_keeps_separate_booked_blocks(self) -> None:
        summary = ScheduleSummary(
            report_date=date(2026, 5, 5),
            spaces=["MC C220.6"],
            periods=[
                PeriodRecord("9:00 AM - 9:30 AM", {"MC C220.6": "Sam Albert"}),
                PeriodRecord("9:30 AM - 10:00 AM", {"MC C220.6": ""}),
                PeriodRecord("10:00 AM - 10:30 AM", {"MC C220.6": "Team Meeting"}),
            ],
        )

        condensed = build_condensed_summary(summary)

        self.assertEqual(len(condensed.by_space["MC C220.6"]), 2)
        self.assertEqual(condensed.by_space["MC C220.6"][0].when, "9 AM - 9:30 AM")
        self.assertEqual(condensed.by_space["MC C220.6"][1].when, "10 AM - 10:30 AM")


if __name__ == "__main__":
    unittest.main()
