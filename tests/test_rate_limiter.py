from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import unittest
from unittest.mock import Mock, patch

from common_utils.rate_limited_task import RateLimitedTask


class RateLimiterTests(unittest.TestCase):
    def test_interval_and_independent_instances(self):
        first = RateLimitedTask(timedelta(seconds=10))
        second = RateLimitedTask(timedelta(seconds=10))
        callback = Mock()
        with patch("common_utils.rate_limiter.monotonic", return_value=0) as monotonic:
            self.assertTrue(first.run(callback))
            self.assertFalse(first.run(callback))
            self.assertTrue(second.run(callback))
            monotonic.return_value = 9.99
            self.assertFalse(first.run(callback))
            monotonic.return_value = 10
            self.assertTrue(first.run(callback))
            self.assertFalse(first.run(callback))
            self.assertTrue(second.run(callback))
        self.assertEqual(callback.call_count, 4)

    def test_concurrent_calls_reserve_one_slot(self):
        limiter = RateLimitedTask(timedelta(seconds=10))
        callback = Mock()
        with patch("common_utils.rate_limiter.monotonic", return_value=0):
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(
                    lambda _: limiter.run(callback), range(100)))
        self.assertEqual(results.count(True), 1)
        callback.assert_called_once_with()

    def test_fractional_interval(self):
        limiter = RateLimitedTask(timedelta(milliseconds=250))
        callback = Mock()
        with patch("common_utils.rate_limiter.monotonic", return_value=0) as monotonic:
            self.assertTrue(limiter.run(callback))
            monotonic.return_value = 0.249
            self.assertFalse(limiter.run(callback))
            monotonic.return_value = 0.25
            self.assertTrue(limiter.run(callback))
        self.assertEqual(callback.call_count, 2)

    def test_callback_failure_propagates_and_reserves_interval(self):
        limiter = RateLimitedTask(timedelta(seconds=10))
        callback = Mock(side_effect=ValueError("failed"))
        with patch("common_utils.rate_limiter.monotonic", return_value=0) as monotonic:
            with self.assertRaisesRegex(ValueError, "failed"):
                limiter.run(callback)
            self.assertFalse(limiter.run(callback))
            callback.assert_called_once_with()
            monotonic.return_value = 10
            with self.assertRaisesRegex(ValueError, "failed"):
                limiter.run(callback)
        self.assertEqual(callback.call_count, 2)


if __name__ == "__main__":
    unittest.main()
