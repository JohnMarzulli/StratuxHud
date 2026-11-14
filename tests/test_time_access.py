from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock, patch

from common_utils.authoritative_time import AuthoritativeTime, to_utc
from common_utils.logger import HudLogger

# Configuration probes the receiver on import; keep these tests entirely offline.
with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from core_services.scope_range import ScopeRange
    from core_services.zoom_tracker import (
        MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE,
        ZoomTracker,
    )
    from data_sources.gdl90_ahrs_source import AhrsStratux


NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)


class SituationTimeTests(unittest.TestCase):
    def setUp(self):
        self.source = AhrsStratux(Mock(spec=HudLogger))
        self.addCleanup(self.source.__stratux_session__.close)
        reporter = patch("data_sources.gdl90_ahrs_source.DISPLAY_TIME.report")
        self.report = reporter.start()
        self.addCleanup(reporter.stop)

    def test_supported_times_are_decoded_and_reported_in_utc(self):
        expected = datetime(2019, 6, 3, 7, 25, 4, 600000, timezone.utc)
        for value in (
            "2019-06-03T07:25:04.6Z",
            "2019-06-03T07:25:04.600000999Z",
            "2019-06-03T09:25:04.6+02:00",
            "2019-06-03T07:25:04.6",
            expected,
            expected.replace(tzinfo=None),
            expected.astimezone(timezone(timedelta(hours=2))),
        ):
            with self.subTest(value=value):
                self.source.__stratux_ahrs_cache__.__data_cache__.update(
                    {"GPSTime": value, "GPSFixQuality": 1, "AHRSPitch": 2.5}
                )
                result = self.source.get_ahrs()
                self.assertEqual(result.utc_time, expected)
                self.assertEqual(result.utc_time.tzinfo, timezone.utc)
                self.assertEqual(result.pitch, 2.5)
                self.report.assert_called_with(expected)

    def test_unavailable_or_invalid_time_does_not_discard_attitude(self):
        for value in (
            None,
            "",
            "0001-01-01T00:00:00Z",
            datetime.min,
            "not a time",
            123,
            {},
            [],
            "9999-12-31T23:59:59-01:00",
        ):
            with self.subTest(value=value):
                self.report.reset_mock()
                self.source.__stratux_ahrs_cache__.__data_cache__.update(
                    {"GPSTime": value, "AHRSPitch": 2.5}
                )
                result = self.source.get_ahrs()
                self.assertIsNone(result.utc_time)
                self.assertEqual(result.pitch, 2.5)
                self.report.assert_not_called()
        self.assertTrue(self.source.__logger__.log_warning_message.called)

    def test_timestamp_without_fractional_seconds(self):
        self.source.__stratux_ahrs_cache__.__data_cache__.update(
            {"GPSTime": "2019-06-03T07:25:04Z"}
        )
        self.assertEqual(
            self.source.get_ahrs().utc_time,
            datetime(2019, 6, 3, 7, 25, 4, tzinfo=timezone.utc),
        )

    def test_empty_and_expired_caches_do_not_report_system_time_as_gps(self):
        self.assertIsNone(self.source.get_ahrs().utc_time)
        self.source.__stratux_ahrs_cache__.__data_cache__.update({
                                                                 "GPSTime": NOW})
        self.source.__stratux_ahrs_cache__.__data_cache__.__last_updated__ -= timedelta(
            seconds=3
        )
        self.assertIsNone(self.source.get_ahrs().utc_time)
        self.report.assert_not_called()

    def test_mocked_rest_updates_merge_avionics_and_stratux(self):
        with patch.object(
            self.source.__stratux_session__,
            "get",
            side_effect=[
                Mock(
                    json=lambda: {
                        "GPSTime": "2019-06-03T07:25:04.6Z",
                        "GPSFixQuality": 1,
                        "GPSLatitude": 47.0,
                    }
                ),
                Mock(json=lambda: {"AHRSPitch": 3.0, "Service": "ToHud"}),
            ],
        ):
            self.source.update()
            self.source.update_avionics()
        result = self.source.get_ahrs()
        self.assertEqual(result.utc_time.year, 2019)
        self.assertEqual(result.pitch, 3.0)
        self.assertEqual(result.position[0], 47.0)
        self.assertTrue(result.is_avionics_source)

    def test_decoded_reports_correct_display_time_without_poisoning_it(self):
        clock = AuthoritativeTime(minimum_report_interval=timedelta(0))
        expected = datetime(2019, 6, 3, 7, 25, 4, 600000, timezone.utc)
        with patch("data_sources.gdl90_ahrs_source.DISPLAY_TIME", clock), patch(
            "common_utils.authoritative_time.get_system_time", return_value=NOW
        ):
            for value in ("2019-06-03T07:25:04.6Z", expected, None, "bad"):
                self.source.__stratux_ahrs_cache__.__data_cache__.update(
                    {"GPSTime": value}
                )
                self.source.get_ahrs()
            self.assertEqual(clock.get_display_time_utc(), expected)


class AuthoritativeTimeTests(unittest.TestCase):
    def test_small_report_window_is_safe_before_first_report(self):
        clock = AuthoritativeTime(maximum_report_count=1)
        with patch("common_utils.authoritative_time.get_system_time", return_value=NOW):
            self.assertEqual(clock.get_display_time_utc(), NOW)
            clock.report(NOW - timedelta(hours=1))
            self.assertEqual(clock.get_display_time_utc(),
                             NOW - timedelta(hours=1))

    def test_display_correction(self):
        for seconds in (-3600, 3600):
            with self.subTest(seconds=seconds):
                clock = AuthoritativeTime(minimum_report_interval=timedelta(0))
                expected = NOW + timedelta(seconds=seconds)
                with patch(
                    "common_utils.authoritative_time.get_system_time",
                    return_value=NOW,
                ):
                    self.assertEqual(clock.get_display_time_utc(), NOW)
                    clock.report(expected)
                    clock.report(expected)
                    self.assertEqual(clock.get_display_time_utc(), expected)

    def test_to_utc_normalizes_external_times(self):
        for value in (
            NOW,
            NOW.replace(tzinfo=None),
            NOW.astimezone(timezone(timedelta(hours=-5))),
        ):
            with self.subTest(value=value):
                result = to_utc(value)
                self.assertEqual(result, NOW)
                self.assertIs(result.tzinfo, timezone.utc)

    def test_report_interval_and_noise_threshold(self):
        for seconds, expected_seconds in ((14, 0), (15, 15), (-15, -15)):
            with self.subTest(seconds=seconds):
                clock = AuthoritativeTime()
                with patch(
                    "common_utils.authoritative_time.get_system_time", return_value=NOW
                ):
                    clock.report(NOW + timedelta(seconds=seconds))
                    clock.report(NOW + timedelta(seconds=seconds))
                    self.assertEqual(clock.get_display_time_utc(), NOW)
                with patch(
                    "common_utils.authoritative_time.get_system_time",
                    return_value=NOW + timedelta(seconds=5),
                ):
                    clock.report(NOW + timedelta(seconds=5 + seconds))
                    self.assertEqual(
                        clock.get_display_time_utc(),
                        NOW + timedelta(seconds=5 + expected_seconds),
                    )


class ZoomTimeTests(unittest.TestCase):
    def test_automatic_zoom_change_can_be_followed_by_another_update(self):
        tracker = ZoomTracker()
        tracker.__last_changed__ -= timedelta(
            seconds=MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE + 1
        )
        tracker.__set_target_zoom__(ScopeRange(5, 10, True))
        tracker.get_target_zoom()
        tracker.__set_target_zoom__(ScopeRange(10, 20, True))
        self.assertIsInstance(tracker.__last_changed__, datetime)


if __name__ == "__main__":
    unittest.main()
