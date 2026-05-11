from __future__ import annotations

import unittest
from datetime import date

from library_schedule.model import PeriodRecord, ScheduleSummary
from library_schedule.transform import trim_summary_rows


class TransformTests(unittest.TestCase):
    def test_trim_first_and_last_rows(self) -> None:
        summary = ScheduleSummary(
            report_date=date(2026, 3, 6),
            spaces=["A"],
            periods=[
                PeriodRecord("r1", {"A": ""}),
                PeriodRecord("r2", {"A": ""}),
                PeriodRecord("r3", {"A": ""}),
                PeriodRecord("r4", {"A": ""}),
                PeriodRecord("r5", {"A": ""}),
                PeriodRecord("r6", {"A": ""}),
            ],
        )

        trimmed = trim_summary_rows(summary, drop_first_rows=3, drop_last_rows=1)
        self.assertEqual([p.period_label for p in trimmed.periods], ["r4", "r5"])


if __name__ == "__main__":
    unittest.main()
