from __future__ import annotations

import unittest

from library_schedule.printing import build_print_command


class PrintingTests(unittest.TestCase):
    def test_builds_default_print_command(self) -> None:
        self.assertEqual(
            build_print_command("output/daily_schedule_2026-05-08.pdf"),
            ["lp", "output/daily_schedule_2026-05-08.pdf"],
        )

    def test_builds_named_printer_command(self) -> None:
        self.assertEqual(
            build_print_command(
                "output/daily_schedule_2026-05-08.pdf",
                printer_name="Media Center Copier",
            ),
            ["lp", "-d", "Media Center Copier", "output/daily_schedule_2026-05-08.pdf"],
        )


if __name__ == "__main__":
    unittest.main()
