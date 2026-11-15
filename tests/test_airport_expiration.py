import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from common_utils.authoritative_time import AuthoritativeTime

# Configuration probes the receiver on import; keep these tests entirely offline.
with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from data_sources.airports import AirportClient, UNKNOWN_EXPIRATION_DATE

NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)


class AirportExpirationTests(unittest.TestCase):
    def setUp(self):
        original = AirportClient.__EXPIRATION_DATE__
        self.addCleanup(setattr, AirportClient,
                        "__EXPIRATION_DATE__", original)
        AirportClient.__EXPIRATION_DATE__ = UNKNOWN_EXPIRATION_DATE

        self.clock = AuthoritativeTime(minimum_report_interval=timedelta(0))
        display_time = patch("data_sources.airports.DISPLAY_TIME", self.clock)
        display_time.start()
        self.addCleanup(display_time.stop)

    def __set_system_time__(self, system_time: datetime):
        patcher = patch(
            "common_utils.authoritative_time.get_system_time",
            return_value=system_time,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_invalid_before_any_status(self):
        self.__set_system_time__(NOW)
        self.assertFalse(AirportClient.is_airport_data_valid())

    def test_stays_invalid_when_display_time_corrects_backwards(self):
        # System clock is a day ahead of GPS, and no status has arrived.
        self.__set_system_time__(NOW + timedelta(days=1))
        self.clock.report(NOW)
        self.clock.report(NOW)
        self.assertEqual(self.clock.get_display_time_utc(), NOW)
        self.assertFalse(AirportClient.is_airport_data_valid())

    def test_valid_until_reported_expiration(self):
        self.__set_system_time__(NOW)
        AirportClient.update_expiration(NOW + timedelta(days=3))
        self.assertTrue(AirportClient.is_airport_data_valid())
        AirportClient.update_expiration(NOW - timedelta(days=1))
        self.assertFalse(AirportClient.is_airport_data_valid())

    def test_none_never_replaces_expiration(self):
        self.__set_system_time__(NOW)
        AirportClient.update_expiration(None)
        self.assertEqual(AirportClient.__EXPIRATION_DATE__,
                         UNKNOWN_EXPIRATION_DATE)
        self.assertFalse(AirportClient.is_airport_data_valid())


if __name__ == "__main__":
    unittest.main()
