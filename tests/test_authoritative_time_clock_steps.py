from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from common_utils.authoritative_time import AuthoritativeTime


class AuthoritativeTimeClockStepTests(unittest.TestCase):
    def test_clock_steps_clear_old_offsets(self):
        now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        for step in (timedelta(hours=-1), timedelta(hours=1)):
            with self.subTest(step=step):
                clock = AuthoritativeTime()
                with patch("common_utils.authoritative_time.get_system_time") as wall, patch(
                    "common_utils.authoritative_time.monotonic"
                ) as monotonic:
                    for elapsed in (0, 5):
                        wall.return_value = now + \
                            timedelta(seconds=elapsed) - step
                        monotonic.return_value = elapsed
                        clock.report(now + timedelta(seconds=elapsed))
                    self.assertEqual(clock.to_display_time(
                        wall.return_value), now + timedelta(seconds=5))

                    wall.return_value = now + timedelta(seconds=10)
                    monotonic.return_value = 10
                    clock.report(wall.return_value - timedelta(seconds=30))
                    self.assertEqual(len(clock.__offset_reports__), 1)
                    self.assertEqual(clock.to_display_time(
                        wall.return_value), wall.return_value)

                    wall.return_value += timedelta(seconds=5)
                    monotonic.return_value = 15
                    clock.report(wall.return_value - timedelta(seconds=30))
                    self.assertEqual(
                        clock.to_display_time(wall.return_value),
                        wall.return_value - timedelta(seconds=30),
                    )

    def test_clock_step_during_interval_clears_offsets_but_preserves_throttle(self):
        now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        clock = AuthoritativeTime(maximum_report_count=8)
        with patch("common_utils.authoritative_time.get_system_time") as wall, patch(
            "common_utils.authoritative_time.monotonic"
        ) as monotonic:
            wall.return_value = now
            monotonic.return_value = 0
            clock.report(now - timedelta(seconds=30))
            self.assertEqual(clock.to_display_time(
                now), now - timedelta(seconds=30))

            wall.return_value = now + timedelta(hours=1, seconds=1)
            monotonic.return_value = 1
            clock.report(wall.return_value - timedelta(seconds=40))
            self.assertEqual(len(clock.__offset_reports__), 0)
            self.assertEqual(clock.to_display_time(
                wall.return_value), wall.return_value)

            wall.return_value += timedelta(seconds=4)
            monotonic.return_value = 5
            clock.report(wall.return_value - timedelta(seconds=40))
            self.assertEqual(len(clock.__offset_reports__), 1)
            self.assertEqual(
                clock.to_display_time(wall.return_value),
                wall.return_value - timedelta(seconds=40),
            )

    def test_small_wall_clock_drift_preserves_history(self):
        now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        clock = AuthoritativeTime(maximum_report_count=8)
        with patch("common_utils.authoritative_time.get_system_time") as wall, patch(
            "common_utils.authoritative_time.monotonic"
        ) as monotonic:
            wall.return_value = now
            monotonic.return_value = 0
            clock.report(now - timedelta(seconds=20))
            wall.return_value = now + timedelta(seconds=5, milliseconds=500)
            monotonic.return_value = 5
            clock.report(wall.return_value - timedelta(seconds=40))
            self.assertEqual(len(clock.__offset_reports__), 2)
            self.assertEqual(
                clock.to_display_time(wall.return_value),
                wall.return_value - timedelta(seconds=30),
            )


if __name__ == "__main__":
    unittest.main()
