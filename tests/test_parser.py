from __future__ import annotations

from datetime import date
import unittest

try:
    from library_schedule.model import FetchedSchedulePage
    from library_schedule.parser import parse_schedule, parse_schedule_pages
except ModuleNotFoundError:  # pragma: no cover
    parse_schedule = None
    parse_schedule_pages = None
    FetchedSchedulePage = None


SAMPLE_HTML = """
<html>
  <body>
    <table id="ignore-me">
      <tr><th>Other</th></tr>
      <tr><td>Not schedule</td></tr>
    </table>
    <table id="schedule">
      <tr>
        <th>Period</th>
        <th>MC C220.6</th>
        <th>MC C220.7</th>
        <th>MC C220.9</th>
        <th>MC Center</th>
        <th>MC Lab North</th>
        <th>MC Lab South</th>
        <th>MC Minneapolis</th>
        <th>MC St. Paul</th>
      </tr>
      <tr>
        <td>Period 1</td>
        <td>Ms. Diaz</td>
        <td>Open</td>
        <td></td>
        <td>Mr. Lee</td>
        <td>-</td>
        <td>Grade 2 Team</td>
        <td>Reserve this time</td>
        <td>Open</td>
      </tr>
      <tr>
        <td>Period 2</td>
        <td></td>
        <td>Mrs. Allen</td>
        <td>Open</td>
        <td>Open</td>
        <td>Robotics</td>
        <td></td>
        <td>Open</td>
        <td>Book Club</td>
      </tr>
    </table>
  </body>
</html>
"""

SHIFTED_HEADER_HTML = """
<html>
  <body>
    <table id="shifted">
      <tr>
        <th>MC C220.6</th>
        <th>MC C220.7</th>
        <th>MC C220.9</th>
        <th>MC Center</th>
        <th>MC Lab North</th>
        <th>MC Lab South</th>
        <th>MC Minneapolis</th>
        <th>MC St. Paul</th>
      </tr>
      <tr>
        <td>First Half Period 1</td>
        <td>Teacher A</td>
        <td>Open</td>
        <td>Open</td>
        <td>Open</td>
        <td>Open</td>
        <td>Teacher B</td>
        <td>Open</td>
        <td>Open</td>
      </tr>
      <tr>
        <td>Second Half Period 1</td>
        <td>Teacher A</td>
        <td>Open</td>
        <td>Open</td>
        <td>Open</td>
        <td>Open</td>
        <td>Teacher B</td>
        <td>Open</td>
        <td>Open</td>
      </tr>
    </table>
  </body>
</html>
"""

MIXED_LINK_TEXT_HTML = """
<html>
  <body>
    <table id="mixed">
      <tr>
        <th>Period</th>
        <th>MC C220.6</th>
        <th>MC C220.7</th>
        <th>MC C220.9</th>
        <th>MC Center</th>
        <th>MC Lab North</th>
        <th>MC Lab South</th>
        <th>MC Minneapolis</th>
        <th>MC St. Paul</th>
      </tr>
      <tr>
        <td>First Half Period 1</td>
        <td>Open</td>
        <td>Open</td>
        <td>Reserve this time Jane Teacher Remove Reservation</td>
        <td>Open</td>
        <td>Open</td>
        <td>Open</td>
        <td>Reserve this time</td>
        <td>Open</td>
      </tr>
    </table>
  </body>
</html>
"""

ROOM_WEEK_HTML = """
<html>
  <body>
    <table id="room-week">
      <tr>
        <th>Week of 5/5</th>
        <th>Monday 5/4</th>
        <th>Tuesday 5/5</th>
      </tr>
      <tr>
        <td>8:30 AM</td>
        <td>Reserve This Time</td>
        <td>speech therapy CHAPUMEL000 Remove Reservation</td>
      </tr>
      <tr>
        <td>9:00 AM</td>
        <td>Reserve This Time</td>
        <td>speech therapy CHAPUMEL000 Remove Reservation</td>
      </tr>
      <tr>
        <td>9:30 AM</td>
        <td>Reserve This Time</td>
        <td>Reserve This Time</td>
      </tr>
    </table>
  </body>
</html>
"""


class ParserTests(unittest.TestCase):
    @unittest.skipIf(parse_schedule is None, "Parser dependencies are not installed.")
    def test_parse_schedule_rows(self) -> None:
        spaces = [
            "MC C220.6",
            "MC C220.7",
            "MC C220.9",
            "MC Center",
            "MC Lab North",
            "MC Lab South",
            "MC Minneapolis",
            "MC St. Paul",
        ]

        summary = parse_schedule(
            html=SAMPLE_HTML,
            target_spaces=spaces,
            room_aliases={space: [space] for space in spaces},
            table_selector="#schedule",
        )

        self.assertEqual(summary.spaces, spaces)
        self.assertEqual(len(summary.periods), 2)
        self.assertEqual(summary.periods[0].period_label, "Period 1")
        self.assertEqual(summary.periods[0].by_space["MC C220.6"], "Ms. Diaz")
        self.assertEqual(summary.periods[0].by_space["MC C220.7"], "")
        self.assertEqual(summary.periods[0].by_space["MC Minneapolis"], "")
        self.assertEqual(summary.periods[1].by_space["MC Lab North"], "Robotics")
        self.assertEqual(summary.periods[1].by_space["MC St. Paul"], "Book Club")

    @unittest.skipIf(parse_schedule is None, "Parser dependencies are not installed.")
    def test_repairs_shifted_room_columns(self) -> None:
        spaces = [
            "MC C220.6",
            "MC C220.7",
            "MC C220.9",
            "MC Center",
            "MC Lab North",
            "MC Lab South",
            "MC Minneapolis",
            "MC St. Paul",
        ]

        summary = parse_schedule(
            html=SHIFTED_HEADER_HTML,
            target_spaces=spaces,
            room_aliases={space: [space] for space in spaces},
            table_selector="#shifted",
        )

        self.assertEqual(summary.periods[0].period_label, "First Half Period 1")
        self.assertEqual(summary.periods[0].by_space["MC C220.6"], "Teacher A")
        self.assertEqual(summary.periods[0].by_space["MC Lab South"], "Teacher B")
        self.assertEqual(summary.periods[0].by_space["MC C220.7"], "")

    @unittest.skipIf(parse_schedule is None, "Parser dependencies are not installed.")
    def test_keeps_booking_when_cell_contains_link_text(self) -> None:
        spaces = [
            "MC C220.6",
            "MC C220.7",
            "MC C220.9",
            "MC Center",
            "MC Lab North",
            "MC Lab South",
            "MC Minneapolis",
            "MC St. Paul",
        ]

        summary = parse_schedule(
            html=MIXED_LINK_TEXT_HTML,
            target_spaces=spaces,
            room_aliases={space: [space] for space in spaces},
            table_selector="#mixed",
        )

        self.assertEqual(summary.periods[0].by_space["MC C220.9"], "Jane Teacher")
        self.assertEqual(summary.periods[0].by_space["MC Minneapolis"], "")

    @unittest.skipIf(parse_schedule_pages is None, "Parser dependencies are not installed.")
    def test_merges_room_week_pages(self) -> None:
        spaces = [
            "MC C220.6",
            "MC C220.7",
            "MC C220.9",
            "MC Center",
            "MC Lab North",
            "MC Lab South",
            "MC Minneapolis",
            "MC St. Paul",
        ]
        pages = [
            FetchedSchedulePage(
                room_name="MC C220.9",
                html=ROOM_WEEK_HTML,
                final_url="http://example.test/room",
            )
        ]

        summary = parse_schedule_pages(
            pages=pages,
            target_spaces=spaces,
            room_aliases={space: [space] for space in spaces},
            report_date=date(2026, 5, 5),
        )

        self.assertEqual(summary.periods[0].period_label, "8:30 AM")
        self.assertEqual(
            summary.periods[0].by_space["MC C220.9"],
            "speech therapy CHAPUMEL000",
        )
        self.assertEqual(summary.periods[2].by_space["MC C220.9"], "")


if __name__ == "__main__":
    unittest.main()
