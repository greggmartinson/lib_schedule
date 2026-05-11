from __future__ import annotations

from datetime import date
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from library_schedule.config import IcsCalendarConfig
from library_schedule.ics_calendar import (
    CalendarFeedError,
    combine_calendar_agendas,
    fetch_calendar_agenda_bundle,
    parse_calendar_agenda,
)
from library_schedule.model import CalendarAgenda, CalendarEvent


SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
X-WR-CALNAME;VALUE=TEXT:Roseville Area High School - 1240 County Road B2 West\\, Roseville\\, MN 55113: Media Center - Mpls Conf Room
BEGIN:VEVENT
DESCRIPTION:Jen Wilson
DTEND:20260511T163000Z
DTSTART:20260511T150000Z
SUMMARY:2526-2050: Homeroom 3rd hour planning
END:VEVENT
BEGIN:VEVENT
DESCRIPTION:Parent Advisory 
 Council
DTEND:20260512T003000Z
DTSTART:20260511T230000Z
SUMMARY:Community Meeting
END:VEVENT
BEGIN:VEVENT
DESCRIPTION:Someone
DTEND:20260511T190000Z
DTSTART:20260511T180000Z
SUMMARY:CANCELLED: 2526-999: Should not show
END:VEVENT
END:VCALENDAR
"""


class IcsCalendarTests(unittest.TestCase):
    def test_parses_and_filters_todays_events(self) -> None:
        agenda = parse_calendar_agenda(
            ics_text=SAMPLE_ICS,
            report_date=date(2026, 5, 11),
            local_tz=ZoneInfo("America/Chicago"),
        )

        self.assertEqual(agenda.source_name, "Media Center - Mpls Conf Room")
        self.assertEqual(len(agenda.events), 2)
        self.assertEqual(agenda.events[0].title, "Homeroom 3rd hour planning")
        self.assertEqual(agenda.events[0].when, "10 AM - 11:30 AM")
        self.assertEqual(agenda.events[0].details, "Jen Wilson")
        self.assertEqual(agenda.events[1].title, "Community Meeting")
        self.assertEqual(agenda.events[1].when, "6 PM - 7:30 PM")
        self.assertEqual(agenda.events[1].details, "Parent Advisory Council")

    def test_combines_multiple_room_calendars_into_media_center_agenda(self) -> None:
        agendas = [
            CalendarAgenda(
                report_date=date(2026, 5, 11),
                source_name="Media Center - Mpls Conf Room",
                events=[
                    CalendarEvent(
                        title="PTSA Meeting - Wilson",
                        when="5 PM - 9 PM",
                        details="Jen Wilson",
                        sort_key="2026-05-11T17:00:00-05:00",
                    )
                ],
            ),
            CalendarAgenda(
                report_date=date(2026, 5, 11),
                source_name="Media Center - C221 Conf Room",
                events=[],
            ),
            CalendarAgenda(
                report_date=date(2026, 5, 11),
                source_name="Media Center - C220",
                events=[
                    CalendarEvent(
                        title="Speech Testing",
                        when="1 PM - 2 PM",
                        details=None,
                        sort_key="2026-05-11T13:00:00-05:00",
                    )
                ],
            ),
        ]

        combined = combine_calendar_agendas(agendas, source_name="Media Center")

        self.assertEqual(combined.source_name, "Media Center")
        self.assertEqual(
            [event.title for event in combined.events],
            ["Speech Testing", "PTSA Meeting - Wilson"],
        )
        self.assertEqual(combined.events[0].details, "C220")
        self.assertEqual(combined.events[1].details, "Mpls Conf Room | Jen Wilson")
        self.assertIsNone(combined.status_note)

    def test_bundle_warnings_include_room_name(self) -> None:
        configs = [
            IcsCalendarConfig(
                url="https://example.test/rooms/513.ics",
                timezone="America/Chicago",
                display_name="C220 - Media Center",
            ),
            IcsCalendarConfig(
                url="https://example.test/rooms/883.ics",
                timezone="America/Chicago",
                display_name="Media Center - Mpls Conf Room",
            ),
        ]
        working_agenda = CalendarAgenda(
            report_date=date(2026, 5, 11),
            source_name="Media Center - Mpls Conf Room",
            events=[],
        )

        with patch(
            "library_schedule.ics_calendar.fetch_calendar_agenda",
            side_effect=[
                CalendarFeedError("Unable to load ICS calendar feed: timeout"),
                working_agenda,
            ],
        ):
            combined, warnings = fetch_calendar_agenda_bundle(configs, date(2026, 5, 11))

        self.assertIsNotNone(combined)
        self.assertEqual(combined.source_name, "Media Center")
        self.assertEqual(
            warnings,
            ["C220 - Media Center: Unable to load ICS calendar feed: timeout"],
        )


if __name__ == "__main__":
    unittest.main()
