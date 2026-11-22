import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pygame

with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from core_services import zoom_tracker
    from core_services.zoom_manager import DEFAULT_ZOOM_INDEX, ZoomManager
    from core_services.zoom_tracker import ZoomTracker
    from views.abstract_elements.top_down_scope import TopDownScope
    from views.adsb_top_view_scope import AdsbTopViewScope
    from views.weather_scope import WeatherTopViewScope

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def key_up(key):
    return pygame.event.Event(pygame.KEYUP, key=key)


class FakeClock:
    def __init__(self):
        self.now = START

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


class ZoomTrackerModeTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        patcher = patch.object(zoom_tracker, "get_system_time", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_starting_zoom_index_is_used(self):
        tracker = ZoomTracker(False, DEFAULT_ZOOM_INDEX + 3)
        expected = ZoomManager(DEFAULT_ZOOM_INDEX + 3).get_current_zoom()

        self.assertEqual(
            tracker.get_target_zoom().max_ring_range, expected.max_ring_range
        )

    def test_manual_only_never_auto_zooms(self):
        tracker = ZoomTracker(allow_automatic=False)
        before = tracker.get_target_zoom().max_ring_range
        self.clock.advance(60)

        fast = Mock(groundspeed=500, airspeed=500)
        tracker.update(fast)

        self.assertEqual(tracker.get_target_zoom().max_ring_range, before)
        self.assertIsNone(tracker.get_zoom_progress())

    def test_manual_only_ignores_return_to_automatic(self):
        tracker = ZoomTracker(allow_automatic=False)
        tracker.return_to_automatic()

        self.assertFalse(tracker.allows_automatic())
        self.assertFalse(tracker.__zoom_manager__.is_automatic())

    def test_manual_zoom_animates_and_reports_direction(self):
        tracker = ZoomTracker()
        start = tracker.get_target_zoom().max_ring_range

        tracker.manual_zoom_out()
        end = tracker.__zoom_manager__.get_current_zoom().max_ring_range
        self.clock.advance(zoom_tracker.SECONDS_FOR_ZOOM / 2)

        self.assertAlmostEqual(
            tracker.get_target_zoom().max_ring_range, (start + end) / 2
        )
        self.assertEqual(tracker.get_zoom_progress()[1], 1)

        self.clock.advance(zoom_tracker.SECONDS_FOR_ZOOM)
        self.assertEqual(tracker.get_target_zoom().max_ring_range, end)
        self.assertIsNone(tracker.get_zoom_progress())

    def test_interrupted_zoom_continues_from_what_is_displayed(self):
        tracker = ZoomTracker()
        tracker.manual_zoom_out()
        self.clock.advance(zoom_tracker.SECONDS_FOR_ZOOM / 2)
        displayed = tracker.get_target_zoom().max_ring_range

        tracker.manual_zoom_in()

        self.assertAlmostEqual(tracker.get_target_zoom().max_ring_range, displayed)
        self.assertEqual(tracker.get_zoom_progress()[1], -1)


class ScopeZoomConfigurationTests(unittest.TestCase):
    def make_scope(self, scope_type):
        scope = scope_type.__new__(scope_type)
        scope.__zoom_tracker__ = ZoomTracker(
            scope_type.ALLOWS_AUTOMATIC_ZOOM, scope_type.STARTING_ZOOM_INDEX
        )
        return scope

    def test_only_differences_are_declared(self):
        self.assertEqual(AdsbTopViewScope.RING_COLOR, (0, 255, 0))
        self.assertTrue(AdsbTopViewScope.ALLOWS_AUTOMATIC_ZOOM)
        self.assertEqual(WeatherTopViewScope.RING_COLOR, (255, 255, 255))
        self.assertFalse(WeatherTopViewScope.ALLOWS_AUTOMATIC_ZOOM)

    def test_both_scopes_share_zoom_handling(self):
        for scope_type in (AdsbTopViewScope, WeatherTopViewScope):
            self.assertIs(scope_type.handle_events, TopDownScope.handle_events)

    def test_seven_returns_adsb_to_automatic(self):
        scope = self.make_scope(AdsbTopViewScope)
        scope.handle_events([key_up(pygame.K_UP)])
        self.assertFalse(scope.__zoom_tracker__.__zoom_manager__.is_automatic())

        remaining = scope.handle_events([key_up(pygame.K_KP7)])

        self.assertEqual(remaining, [])
        self.assertTrue(scope.__zoom_tracker__.__zoom_manager__.is_automatic())

    def test_seven_is_passed_on_by_weather(self):
        scope = self.make_scope(WeatherTopViewScope)

        remaining = scope.handle_events([key_up(pygame.K_KP7)])

        self.assertEqual(len(remaining), 1)
        self.assertFalse(scope.__zoom_tracker__.__zoom_manager__.is_automatic())

    def test_arrow_keys_zoom_both_scopes(self):
        for scope_type in (AdsbTopViewScope, WeatherTopViewScope):
            scope = self.make_scope(scope_type)
            start = scope.__zoom_tracker__.__zoom_manager__.get_current_zoom()

            scope.handle_events([key_up(pygame.K_DOWN)])

            zoomed = scope.__zoom_tracker__.__zoom_manager__.get_current_zoom()
            self.assertLess(zoomed.max_ring_range, start.max_ring_range)


if __name__ == "__main__":
    unittest.main()
