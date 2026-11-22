import unittest
from unittest.mock import Mock, patch

with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from core_services.scope_range import ScopeRange
    from data_sources.traffic import Traffic
    from views.abstract_elements.top_down_scope import TopDownScope
    from views.adsb_top_view_scope import AdsbTopViewScope

SCOPE_RANGE = ScopeRange(2, 5, True)
# Beyond the "always show" inner radius (center ring / 2).
FAR = 1.5
NEAR = 0.5


class ShouldDrawIdentifierTests(unittest.TestCase):
    def setUp(self):
        self.scope = TopDownScope.__new__(TopDownScope)

    def should_draw(self, relative_angle, distance=FAR):
        return self.scope.__should_draw_identifier__(
            relative_angle, distance, SCOPE_RANGE
        )

    def test_ahead_is_drawn(self):
        for angle in (0, 45, -45, 89, -89):
            self.assertTrue(self.should_draw(angle), angle)

    def test_behind_is_hidden(self):
        for angle in (90, -90, 135, 180, -180):
            self.assertFalse(self.should_draw(angle), angle)

    def test_angles_across_north_are_folded(self):
        # Heading 350, bearing 010 -> -340, really 20 degrees right.
        self.assertTrue(self.should_draw(10 - 350))
        # Heading 010, bearing 350 -> 340, really 20 degrees left.
        self.assertTrue(self.should_draw(350 - 10))
        # Heading 010, bearing 190 -> 180, directly behind.
        self.assertFalse(self.should_draw(190 - 10))

    def test_close_targets_are_drawn_even_behind(self):
        self.assertTrue(self.should_draw(180, NEAR))


class TrafficIdentifierTests(unittest.TestCase):
    def make_scope(self):
        scope = AdsbTopViewScope.__new__(AdsbTopViewScope)
        scope.__width__, scope.__height__ = 100, 100
        scope.__zoom_tracker__ = Mock()
        scope.__zoom_tracker__.is_in_range.return_value = (True, FAR)
        scope.__get_pixel_distance__ = Mock(return_value=5)
        scope.__get_screen_projection_from_center__ = Mock(return_value=(50, 50))
        scope.__get_traffic_indicator__ = Mock(
            return_value=[[50, 45], [45, 55], [55, 55]]
        )
        scope.__render_prediction__ = Mock()
        scope.__render_centered_text__ = Mock()
        scope.__draw_identifiers__ = True
        scope.__reduced_visuals__ = False
        scope.__no_direction_target_size__ = 2
        scope.__font_half_height__ = 5
        return scope

    def render(self, gps_heading, traffic_bearing, compass_heading=""):
        scope = self.make_scope()
        traffic = Traffic("123", {
            "displayName": "N123", "Lat": 0.01, "Lng": 0, "Alt": 1000,
            "Distance": 5280, "Bearing": traffic_bearing, "Track": 0,
        })
        # A compass that is missing ("") must not matter; the scope
        # judges "ahead" from the GPS track it draws with.
        orientation = Mock(
            position=[0, 0], alt=900, compass_heading=compass_heading
        )
        orientation.get_precise_gps_heading.return_value = gps_heading

        with patch("views.adsb_top_view_scope.drawing.renderer.polygon"):
            scope.__render_on_screen_target__(
                None, orientation, traffic, SCOPE_RANGE
            )

        return scope.__render_centered_text__.called

    def test_traffic_just_across_north_is_labeled(self):
        self.assertTrue(self.render(gps_heading=350, traffic_bearing=10))

    def test_traffic_behind_is_not_labeled(self):
        self.assertFalse(self.render(gps_heading=10, traffic_bearing=190))

    def test_missing_compass_does_not_crash(self):
        self.assertTrue(self.render(gps_heading=0, traffic_bearing=0))


if __name__ == "__main__":
    unittest.main()
