from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from forgel import peak
from forgel.config import Settings
from forgel.project_config import render_project_config

UTC = timezone.utc


class WindowTest(unittest.TestCase):
    def test_parse_hours(self) -> None:
        self.assertEqual(peak.parse_hours("1-4,6-10"), [(1, 4), (6, 10)])
        for bad in ("", "4-1", "a-b", "0-25"):
            with self.subTest(spec=bad):
                with self.assertRaises(ValueError):
                    peak.parse_hours(bad)

    def test_weekday_windows(self) -> None:
        hour = peak.parse_hours("1-4")
        self.assertFalse(peak.is_off_peak(datetime(2026, 11, 16, 2, 0, tzinfo=UTC), "1-4"))
        self.assertTrue(peak.is_off_peak(datetime(2026, 11, 16, 5, 0, tzinfo=UTC), "1-4"))
        # 2026-11-14 is a Saturday: always off-peak.
        self.assertTrue(peak.is_off_peak(datetime(2026, 11, 14, 2, 0, tzinfo=UTC), "1-4"))

    def test_next_off_peak_is_the_window_close(self) -> None:
        self.assertEqual(
            peak.next_off_peak(datetime(2026, 11, 16, 2, 30, tzinfo=UTC), "1-4"),
            datetime(2026, 11, 16, 4, 0, tzinfo=UTC),
        )
        self.assertEqual(
            peak.seconds_until_off_peak(
                datetime(2026, 11, 16, 2, 30, tzinfo=UTC), "1-4"
            ),
            5400,
        )

    def test_next_peak_starts_at_the_window(self) -> None:
        # Monday 00:30 → peak starts at 01:00.
        self.assertEqual(
            peak.next_peak(datetime(2026, 11, 16, 0, 30, tzinfo=UTC), "1-4"),
            datetime(2026, 11, 16, 1, 0, tzinfo=UTC),
        )

    def test_policy_decides(self) -> None:
        now = datetime(2026, 11, 16, 2, 0, tzinfo=UTC)
        self.assertTrue(peak.should_defer("off_peak", now, "1-4"))
        self.assertFalse(peak.should_defer("always", now, "1-4"))
        self.assertFalse(
            peak.should_defer("off_peak", datetime(2026, 11, 16, 12, 0, tzinfo=UTC), "1-4")
        )

    def test_defer_message_names_the_boundary_and_the_override(self) -> None:
        message = peak.defer_message(
            datetime(2026, 11, 16, 2, 30, tzinfo=UTC), "1-4"
        )
        self.assertIn("04:00 UTC", message)
        self.assertIn("/peak always", message)
        self.assertIn("01:00-04:00 UTC", message)

    def test_status_text(self) -> None:
        text = peak.status_text(
            "off_peak", datetime(2026, 11, 16, 2, 30, tzinfo=UTC), "1-4"
        )
        self.assertIn("Peak policy: off_peak", text)
        self.assertIn("Now: peak", text)
        self.assertIn("Next off-peak: 04:00 UTC", text)


class ProjectPolicyTest(unittest.TestCase):
    def test_falls_back_to_the_runtime_setting(self) -> None:
        settings = Settings(home=Path("/tmp/x"), registry_path=Path("/x"),
                            templates_path=Path("/x"), jurisdiction_path=Path("/x"),
                            peak_policy="off_peak")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                peak.project_policy(settings, Path(tmp)), "off_peak"
            )

    def test_project_config_wins(self) -> None:
        settings = Settings(home=Path("/tmp/x"), registry_path=Path("/x"),
                            templates_path=Path("/x"), jurisdiction_path=Path("/x"),
                            peak_policy="off_peak")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text(
                render_project_config("demo", model_peak_policy="always"),
                encoding="utf-8",
            )
            self.assertEqual(
                peak.project_policy(settings, Path(tmp)), "always"
            )


if __name__ == "__main__":
    unittest.main()
