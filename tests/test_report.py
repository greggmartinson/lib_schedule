from __future__ import annotations

from datetime import date
import unittest

from library_schedule.model import CondensedScheduleSummary, SummaryEntry
from library_schedule.report import render_summary_table_fragment


class ReportTests(unittest.TestCase):
    def test_summary_fragment_strips_directory_style_suffixes(self) -> None:
        summary = CondensedScheduleSummary(
            report_date=date(2026, 5, 8),
            spaces=["MC C220.9"],
            by_space={
                "MC C220.9": [
                    SummaryEntry(
                        booking="speech therapy CHAPUMEL000",
                        when="9:30 AM - 5 PM",
                    )
                ]
            },
        )

        html = render_summary_table_fragment(summary)

        self.assertIn("speech therapy", html)
        self.assertNotIn("CHAPUMEL000", html)


if __name__ == "__main__":
    unittest.main()
