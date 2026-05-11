from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from library_schedule.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_multiple_ics_calendars(self) -> None:
        config_text = """
schedule_url: "http://example.test/computerlab/reserve/"
ics_calendars:
  - url: "https://example.test/rooms/460.ics"
    timezone: "America/Chicago"
    display_name: "Media Center - Center & Comp Lab"
  - url: "https://example.test/rooms/513.ics"
    timezone: "America/Chicago"
    display_name: "C220 - Media Center"
"""

        config = self._load_temp_config(config_text)

        self.assertEqual(len(config.ics_calendars), 2)
        self.assertEqual(
            [item.display_name for item in config.ics_calendars],
            ["Media Center - Center & Comp Lab", "C220 - Media Center"],
        )

    def test_loads_legacy_single_ics_calendar(self) -> None:
        config_text = """
schedule_url: "http://example.test/computerlab/reserve/"
ics_calendar:
  url: "https://example.test/rooms/883.ics"
  timezone: "America/Chicago"
  display_name: "Media Center - Mpls Conf Room"
"""

        config = self._load_temp_config(config_text)

        self.assertEqual(len(config.ics_calendars), 1)
        self.assertEqual(
            config.ics_calendars[0].display_name,
            "Media Center - Mpls Conf Room",
        )

    def _load_temp_config(self, config_text: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.yaml"
            path.write_text(config_text.strip(), encoding="utf-8")
            return load_config(path)


if __name__ == "__main__":
    unittest.main()
