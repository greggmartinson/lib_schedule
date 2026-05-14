from __future__ import annotations

from datetime import date
import unittest

from library_schedule.booking_text import clean_booking_for_display
from library_schedule.google_slides import (
    _build_title_date_text,
    _build_title_text,
    extract_presentation_id,
    format_calendar_card_text,
    format_room_card_text,
)
from library_schedule.model import CalendarAgenda, CalendarEvent, CondensedScheduleSummary, SummaryEntry


class GoogleSlidesTests(unittest.TestCase):
    def test_extracts_presentation_id_from_url(self) -> None:
        value = (
            "https://docs.google.com/presentation/d/"
            "12lNrWDhZ95yRpCrf2LoMvkxFhbHJz7WEUAv-asPhgdU/edit"
            "?slide=id.g3e7c148e447_1_0#slide=id.g3e7c148e447_1_0"
        )

        self.assertEqual(
            extract_presentation_id(value),
            "12lNrWDhZ95yRpCrf2LoMvkxFhbHJz7WEUAv-asPhgdU",
        )

    def test_formats_room_card_text(self) -> None:
        entries = [
            SummaryEntry(booking="Sam Albert", when="9 AM - 3:30 PM"),
            SummaryEntry(booking="Team Meeting", when="4 PM - 5 PM"),
        ]

        text = format_room_card_text("MC C220.6", entries)

        self.assertEqual(
            text,
            "MC C220.6\nSam Albert\n9 AM - 3:30 PM\n\nTeam Meeting\n4 PM - 5 PM",
        )

    def test_formats_free_room_card_text(self) -> None:
        self.assertEqual(format_room_card_text("MC C220.7", []), "MC C220.7\nFree all day")

    def test_formats_calendar_card_text(self) -> None:
        agenda = CalendarAgenda(
            report_date=date(2026, 5, 11),
            source_name="Mpls Conf Room",
            events=[
                CalendarEvent(
                    title="Homeroom 3rd hour planning",
                    when="2:50 PM - 3:30 PM",
                    details="Jen Wilson",
                )
            ],
        )

        self.assertEqual(
            format_calendar_card_text(agenda),
            "Mpls Conf Room Events\nHomeroom 3rd hour planning\n2:50 PM - 3:30 PM\nJen Wilson",
        )

    def test_formats_slide_title_and_date(self) -> None:
        self.assertEqual(_build_title_text(), "Today's Guests")
        self.assertEqual(
            _build_title_date_text(
                CondensedScheduleSummary(
                    report_date=date(2026, 5, 11),
                    spaces=[],
                    by_space={},
                )
            ),
            "Monday, May 11, 2026",
        )

    def test_strips_directory_style_suffixes(self) -> None:
        self.assertEqual(clean_booking_for_display("LaTrell Williams SMITHDEL001"), "LaTrell Williams")


if __name__ == "__main__":
    unittest.main()
