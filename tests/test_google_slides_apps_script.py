from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from library_schedule.booking_text import clean_booking_for_display
from library_schedule.config import GoogleSlidesConfig
from library_schedule.google_slides_apps_script import (
    build_apps_script_payload,
    render_apps_script_submit_page,
)
from library_schedule.model import CondensedScheduleSummary, SummaryEntry


class GoogleSlidesAppsScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GoogleSlidesConfig(
            presentation_url=(
                "https://docs.google.com/presentation/d/"
                "12lNrWDhZ95yRpCrf2LoMvkxFhbHJz7WEUAv-asPhgdU/edit"
            ),
            slide_index=2,
            oauth_client_secret_path=Path("config/google_oauth_client_secret.json"),
            oauth_token_path=Path(".auth/google_slides_token.json"),
            apps_script_web_app_url="https://script.google.com/macros/s/example/exec",
        )
        self.summary = CondensedScheduleSummary(
            report_date=date(2026, 5, 7),
            spaces=["MC C220.6", "MC C220.7"],
            by_space={
                "MC C220.6": [
                    SummaryEntry(booking="Sam Albert SMITHDEL001", when="9 AM - 3:30 PM")
                ],
                "MC C220.7": [],
            },
        )

    def test_builds_apps_script_payload(self) -> None:
        payload = build_apps_script_payload(self.summary, self.config)

        self.assertEqual(
            payload["presentationId"],
            "12lNrWDhZ95yRpCrf2LoMvkxFhbHJz7WEUAv-asPhgdU",
        )
        self.assertEqual(payload["slideIndex"], 2)
        self.assertEqual(payload["reportDateIso"], "2026-05-07")
        self.assertEqual(payload["reportDateLabel"], "Thursday, May 7, 2026")
        self.assertEqual(payload["rooms"][0]["entries"][0]["booking"], "Sam Albert")
        self.assertEqual(payload["rooms"][1]["entries"], [])

    def test_renders_submit_page(self) -> None:
        payload = build_apps_script_payload(self.summary, self.config)
        html = render_apps_script_submit_page(
            payload=payload,
            web_app_url=self.config.apps_script_web_app_url or "",
        )

        self.assertIn('action="https://script.google.com/macros/s/example/exec"', html)
        self.assertIn("Sam Albert", html)
        self.assertIn("Submit Schedule Update", html)

    def test_strips_directory_style_suffixes(self) -> None:
        self.assertEqual(clean_booking_for_display("speech therapy CHAPUMEL000"), "speech therapy")
        self.assertEqual(clean_booking_for_display("VRS Sam Albert martigre000"), "VRS Sam Albert")


if __name__ == "__main__":
    unittest.main()
