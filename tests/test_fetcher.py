from __future__ import annotations

from pathlib import Path
import unittest

from library_schedule.config import AppConfig
from library_schedule.fetcher import (
    _find_link_for_aliases,
    _format_browser_launch_error,
    _looks_like_schedule_page,
    _wait_for_authenticated_schedule_page,
)
from playwright.sync_api import Error as PlaywrightError


class FetcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig(
            schedule_url="http://example.test/computerlab/reserve/",
            target_spaces=["MC C220.6", "MC C220.7"],
            room_aliases={
                "MC C220.6": ["MC C220.6"],
                "MC C220.7": ["MC C220.7"],
            },
            schedule_table_selector=None,
            drop_first_period_rows=0,
            drop_last_period_rows=0,
            auth_storage_state_path=Path(".auth/storage_state.json"),
            browser_timeout_ms=45000,
            default_headless=True,
            google_slides=None,
            ics_calendars=[],
        )

    def test_matches_room_link_with_hyphenated_label(self) -> None:
        anchors = [
            {
                "text": "MC - C220.6",
                "href": "picklab.cfm?picklab=SSS1&date=05-05-2026",
            },
            {
                "text": "MC Center",
                "href": "picklab.cfm?picklab=mctrchairs&date=05-05-2026",
            },
        ]

        match = _find_link_for_aliases(
            anchors=anchors,
            aliases=["MC C220.6"],
            base_url="http://example.test/computerlab/reserve/index.cfm?date=05-05-2026",
        )

        self.assertEqual(
            match,
            "http://example.test/computerlab/reserve/picklab.cfm?picklab=SSS1&date=05-05-2026",
        )

    def test_detects_authenticated_schedule_page(self) -> None:
        html = """
        <html>
          <body>
            <table>
              <tr><th>Period/Time</th><th>MC C220.6</th><th>MC C220.7</th></tr>
              <tr><td>8:00 AM - 8:30 AM</td><td>Reserve this time</td><td>Open</td></tr>
            </table>
          </body>
        </html>
        """

        self.assertTrue(
            _looks_like_schedule_page(
                "http://example.test/computerlab/reserve/",
                html,
                self.config,
            )
        )

    def test_wait_for_authenticated_schedule_page_retries_navigation_errors(self) -> None:
        schedule_html = """
        <html>
          <body>
            <table>
              <tr><th>Period/Time</th><th>MC C220.6</th><th>MC C220.7</th></tr>
              <tr><td>8:00 AM - 8:30 AM</td><td>Reserve this time</td><td>Open</td></tr>
            </table>
          </body>
        </html>
        """

        class FakePage:
            def __init__(self) -> None:
                self.url = "http://example.test/computerlab/reserve/"
                self._responses = [
                    PlaywrightError(
                        "Unable to retrieve content because the page is navigating and changing the content."
                    ),
                    schedule_html,
                ]

            def wait_for_timeout(self, _: int) -> None:
                return None

            def is_closed(self) -> bool:
                return False

            def content(self) -> str:
                response = self._responses.pop(0)
                if isinstance(response, Exception):
                    raise response
                return response

        _wait_for_authenticated_schedule_page(FakePage(), self.config)

    def test_formats_missing_playwright_browser_error(self) -> None:
        error = PlaywrightError(
            "BrowserType.launch: Executable doesn't exist at "
            "/Users/example/Library/Caches/ms-playwright/chromium-1208/chrome"
        )

        message = _format_browser_launch_error(error)

        self.assertIn("Playwright browser runtime is missing.", message)
        self.assertIn(".venv/bin/playwright install chromium", message)


if __name__ == "__main__":
    unittest.main()
