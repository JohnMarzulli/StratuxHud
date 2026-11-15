from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from common_utils.authoritative_time import AuthoritativeTime


class AuthoritativeTimeReportWindowTests(unittest.TestCase):
    def test_retains_configured_reports_and_evicts_oldest(self):
        now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        for capacity in (1, 2, 20):
            with self.subTest(capacity=capacity):
                clock = AuthoritativeTime(
                    minimum_report_interval=timedelta(0),
                    maximum_report_count=capacity,
                )
                with patch("common_utils.authoritative_time.get_system_time", return_value=now), patch(
                    "common_utils.authoritative_time.monotonic", return_value=0
                ):
                    for index in range(capacity + 1):
                        offset = timedelta(seconds=20 + index * 2)
                        clock.report(now - offset)
                        expected_offsets = [
                            timedelta(seconds=20 + position * 2)
                            for position in range(max(0, index - capacity + 1), index + 1)
                        ]
                        self.assertEqual(
                            [report.get_offset() for report in clock.__offset_reports__],
                            expected_offsets,
                        )
                        if len(expected_offsets) >= max(1, int(capacity / 8)):
                            self.assertEqual(
                                clock.to_display_time(now),
                                now - sum(expected_offsets, timedelta(0)) / len(expected_offsets),
                            )


if __name__ == "__main__":
    unittest.main()