from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event, Lock
import unittest
from unittest.mock import patch

from common_utils.authoritative_time import AuthoritativeTime, __TimeOffsetReport__


class TrackingLock:
    def __init__(self):
        self.lock = Lock()
        self.waiting = Event()

    def __enter__(self):
        if self.lock.locked():
            self.waiting.set()
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()


class AuthoritativeTimeConcurrencyTests(unittest.TestCase):
    def test_concurrent_reports_serialize_acceptance_and_mean(self):
        now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        for interval, expected_count, expected_offset in (
            (timedelta(0), 2, timedelta(seconds=30)),
            (timedelta(seconds=5), 1, timedelta(seconds=20)),
        ):
            with self.subTest(interval=interval):
                clock = AuthoritativeTime(
                    minimum_report_interval=interval, maximum_report_count=8
                )
                lock = TrackingLock()
                calculating = Event()
                release = Event()
                original_get_offset = __TimeOffsetReport__.get_offset

                def blocked_get_offset(report):
                    calculating.set()
                    if not release.wait(5):
                        raise TimeoutError("Mean calculation did not resume")
                    return original_get_offset(report)

                with patch(
                    "common_utils.authoritative_time.get_system_time", return_value=now
                ), patch.object(__TimeOffsetReport__, "get_offset", blocked_get_offset), patch.object(
                    clock, "__report_lock__", lock
                ):
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        first = executor.submit(
                            clock.report, now - timedelta(seconds=20))
                        try:
                            self.assertTrue(calculating.wait(5))
                            second = executor.submit(
                                clock.report, now - timedelta(seconds=40))
                            self.assertTrue(lock.waiting.wait(5))
                            self.assertEqual(len(clock.__offset_reports__), 1)
                            self.assertFalse(second.done())
                        finally:
                            release.set()
                        first.result(timeout=5)
                        second.result(timeout=5)

                self.assertEqual(len(clock.__offset_reports__), expected_count)
                self.assertEqual(clock.to_display_time(now),
                                 now - expected_offset)


if __name__ == "__main__":
    unittest.main()
