import io
import json
import logging
import pathlib
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from common_utils.authoritative_time import AuthoritativeTime
from common_utils.logger import DisplayTimeFormatter, HudLogger

# Configuration probes the receiver on import; keep these tests entirely offline.
with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from data_sources.gdl90_ahrs_source import AhrsStratux

FRAMES_PATH = (
    pathlib.Path(__file__).parent.parent
    / "test_data"
    / "stratux_get_situation_frames.json"
)

# A system clock that is a full day behind GPS (e.g. a Pi without an RTC).
SYSTEM_CLOCK_ERROR = timedelta(days=-1)


def make_record(created: datetime) -> logging.LogRecord:
    record = logging.LogRecord(
        "test", logging.INFO, __file__, 1, "msg", None, None)
    record.created = created.timestamp()
    return record


class DisplayTimeFormatterTests(unittest.TestCase):
    def test_uses_system_time_before_any_reports(self):
        created = datetime(2026, 11, 14, 21, 5, 58, 123456, timezone.utc)
        formatter = DisplayTimeFormatter(clock=AuthoritativeTime())
        self.assertEqual(
            formatter.formatTime(make_record(
                created)), "2026-11-14 21:05:58.123Z"
        )

    def test_whole_second_has_consistent_width(self):
        created = datetime(2026, 11, 14, 21, 5, 58, tzinfo=timezone.utc)
        formatter = DisplayTimeFormatter(clock=AuthoritativeTime())
        self.assertEqual(
            formatter.formatTime(make_record(
                created)), "2026-11-14 21:05:58.000Z"
        )

    def test_custom_date_format(self):
        created = datetime(2026, 11, 14, 21, 5, 58, tzinfo=timezone.utc)
        formatter = DisplayTimeFormatter(
            datefmt="%H:%M:%SZ", clock=AuthoritativeTime()
        )
        self.assertEqual(formatter.formatTime(
            make_record(created)), "21:05:58Z")

    def test_log_timestamps_follow_gps_from_captured_frames(self):
        frames = json.loads(FRAMES_PATH.read_text())
        source = AhrsStratux(Mock(spec=HudLogger))
        self.addCleanup(source.__stratux_session__.close)
        clock = AuthoritativeTime(minimum_report_interval=timedelta(0))

        last_gps_time = None
        for frame in frames:
            gps_time = source.__decode_situation__(frame).utc_time
            system_now = gps_time + SYSTEM_CLOCK_ERROR
            with patch(
                "common_utils.authoritative_time.get_system_time",
                return_value=system_now,
            ):
                clock.report(gps_time)
            last_gps_time, last_system_time = gps_time, system_now

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(DisplayTimeFormatter(
            "%(asctime)s %(message)s", clock=clock))
        python_logger = logging.getLogger("test_log_time")
        python_logger.propagate = False
        python_logger.addHandler(handler)
        self.addCleanup(python_logger.removeHandler, handler)

        with patch("time.time", return_value=last_system_time.timestamp()), patch(
            "time.time_ns", return_value=int(last_system_time.timestamp() * 1e9)
        ):
            python_logger.warning("hello")

        expected = last_gps_time.strftime("%Y-%m-%d %H:%M:%S.") + "%03dZ" % (
            last_gps_time.microsecond // 1000
        )
        self.assertEqual(stream.getvalue().strip(), f"{expected} hello")

    def test_default_clock_is_display_time(self):
        clock = AuthoritativeTime()
        created = datetime(2026, 11, 14, 21, 5, 58, tzinfo=timezone.utc)
        with patch("common_utils.logger.DISPLAY_TIME", clock), patch.object(
            clock, "to_display_time", return_value=created + timedelta(hours=1)
        ) as converted:
            text = DisplayTimeFormatter().formatTime(make_record(created))
        converted.assert_called_once_with(created)
        self.assertEqual(text, "2026-11-14 22:05:58.000Z")


class ToDisplayTimeTests(unittest.TestCase):
    def test_matches_get_display_time_utc(self):
        now = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
        clock = AuthoritativeTime(minimum_report_interval=timedelta(0))
        with patch(
            "common_utils.authoritative_time.get_system_time", return_value=now
        ):
            clock.report(now + timedelta(hours=2))
            clock.report(now + timedelta(hours=2))
            self.assertEqual(clock.get_display_time_utc(),
                             now + timedelta(hours=2))
            self.assertEqual(clock.to_display_time(
                now), clock.get_display_time_utc())


if __name__ == "__main__":
    unittest.main()
