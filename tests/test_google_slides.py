from __future__ import annotations

import unittest

from library_schedule.booking_text import clean_booking_for_display
from library_schedule.google_slides import extract_presentation_id, format_room_card_text
from library_schedule.model import SummaryEntry


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

    def test_strips_directory_style_suffixes(self) -> None:
        self.assertEqual(clean_booking_for_display("LaTrell Williams SMITHDEL001"), "LaTrell Williams")


if __name__ == "__main__":
    unittest.main()
