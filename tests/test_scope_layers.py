import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from views.scope_layers.marker_set import MarkerSet
from views.scope_layers.scope_canvas import ScopeCanvas
from views.scope_layers.scope_marker import ScopeMarker
from views.scope_layers import marker_layer

with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from common_utils import geo_math, units
    from core_services import traffic_threat
    from core_services.scope_range import ScopeRange
    from data_sources.ahrs_data import AhrsData
    from data_sources.airports import AirportClient
    from data_sources.data_cache import HudDataCache
    from data_sources.traffic import Traffic
    from views.scope_layers import (
        AirportLayer,
        BreadcrumbLayer,
        MarkerLayer,
        ScopeFrame,
        TrafficLayer,
        WeatherLayer,
    )
    from views.scope_layers import breadcrumb_layer, weather_layer
    from views.scope_layers import DetailRule, airport_layer, traffic_layer

ORIGIN = [47.0, -122.0]
SCOPE_RANGE = ScopeRange(2, 5, True)
FAR = 1.5  # Inside the center ring, outside its "always show" half
NEAR = 0.5


def make_canvas(width=800, height=480, line_width=3):
    host = SimpleNamespace(
        __width__=width,
        __height__=height,
        __left_border__=8,
        __right_border__=width - 8,
        __bottom_border__=height - 5,
        __font_height__=40,
        __font_half_height__=20,
        __line_width__=line_width,
        __thin_line_width__=max(1, line_width >> 1),
        __reduced_visuals__=False,
        __cluter_visuals__=False,
        __render_centered_text__=Mock(),
        __render_text__=Mock(),
        __render_text_right_justified__=Mock(),
    )

    return ScopeCanvas(host, [width // 2, int(height * 0.75)], int(height * 0.74))


def make_orientation(heading=0.0, position=None, gps_online=True):
    orientation = AhrsData()
    orientation.gps_heading = heading
    orientation.compass_heading = ""  # A missing compass must not matter
    orientation.position = list(position or ORIGIN)
    orientation.gps_online = gps_online
    orientation.alt = 900

    return orientation


def make_frame(canvas=None, heading=0.0, scope_range=SCOPE_RANGE,
               display_units=units.STATUTE, **orientation_options):
    return ScopeFrame(
        canvas or make_canvas(),
        None,
        make_orientation(heading, **orientation_options),
        scope_range,
        display_units,
    )


def offset(origin, bearing, statute_miles):
    import math

    radians = math.radians(bearing)
    d_lat = math.cos(radians) * statute_miles / 69.0
    d_lon = math.sin(radians) * statute_miles / (69.0 * math.cos(math.radians(origin[0])))

    return [origin[0] + d_lat, origin[1] + d_lon]


def traffic_at(coordinates, identifier="N123", **extra):
    """
    Traffic reported (in raw yards, like the receiver) at the exact
    distance and bearing of the given coordinates.
    """
    report = {
        "displayName": identifier,
        "Lat": coordinates[0],
        "Lng": coordinates[1],
        "Alt": 1000,
        "Distance": geo_math.get_distance(ORIGIN, coordinates) * units.yards_to_sm,
        "Bearing": geo_math.get_bearing(ORIGIN, coordinates),
        "Track": 0,
    }
    report.update(extra)
    # A None value means "not reported", so leave the key out.
    report = {key: value for key, value in report.items() if value is not None}

    return Traffic(identifier, report)


def airport_at(coordinates, ident="KTST"):
    return {
        "coordinates": {"latitude": coordinates[0], "longitude": coordinates[1]},
        "ident": ident,
        "flightRules": "VFR",
    }


def point(latitude, longitude, altitude=1000):
    return {"Lat": latitude, "Lng": longitude, "Alt": altitude, "secondsAhead": 0, "Track": 0}


class DetailRuleTests(unittest.TestCase):
    """
    Which markers get labels: inside the center ring, and ahead of us
    or really close.
    """

    def is_detailed(self, bearing, distance=FAR, heading=0.0, rule=DetailRule()):
        marker = ScopeMarker(distance=distance, bearing=bearing, color=[255, 0, 0])

        return rule(marker, make_frame(heading=heading)) > 0.0

    def test_ahead_is_detailed(self):
        for bearing in (0, 45, 315, 89, 271):
            self.assertTrue(self.is_detailed(bearing), bearing)

    def test_behind_is_simple(self):
        for bearing in (90, 270, 135, 180, 225):
            self.assertFalse(self.is_detailed(bearing), bearing)

    def test_angles_across_north_are_folded(self):
        # Heading 350, bearing 010: 20 degrees right, nearly ahead.
        self.assertTrue(self.is_detailed(10, heading=350))
        # Heading 010, bearing 350: 20 degrees left.
        self.assertTrue(self.is_detailed(350, heading=10))
        # Heading 010, bearing 190: directly behind.
        self.assertFalse(self.is_detailed(190, heading=10))

    def test_close_markers_are_detailed_even_behind(self):
        self.assertTrue(self.is_detailed(180, NEAR))

    def test_outside_the_center_ring_is_simple(self):
        self.assertFalse(self.is_detailed(0, SCOPE_RANGE.center_ring_range + 0.1))

    def test_defaults_match_the_original_rule(self):
        for rule in (DetailRule(), traffic_layer.TRAFFIC_DETAIL_RULE.rule,
                     airport_layer.AIRPORT_DETAIL_RULE):
            self.assertEqual(
                (rule.max_distance_rings, rule.ahead_half_angle, rule.always_within_rings),
                (1.0, 90.0, 0.5),
            )

    def test_wider_ahead_angle(self):
        everywhere = DetailRule(ahead_half_angle=180.0)
        for bearing in (90, 135, 180, 270):
            self.assertTrue(self.is_detailed(bearing, rule=everywhere), bearing)

    def test_narrower_ahead_angle(self):
        narrow = DetailRule(ahead_half_angle=45.0)
        self.assertTrue(self.is_detailed(30, rule=narrow))
        self.assertFalse(self.is_detailed(60, rule=narrow))

    def test_max_distance(self):
        out_to_outer_ring = DetailRule(max_distance_rings=2.0)
        beyond_center_ring = SCOPE_RANGE.center_ring_range + 1
        self.assertTrue(self.is_detailed(0, beyond_center_ring, rule=out_to_outer_ring))
        self.assertFalse(self.is_detailed(0, rule=DetailRule(max_distance_rings=0.0)))

    def test_always_within(self):
        none_close = DetailRule(always_within_rings=0.0)
        self.assertFalse(self.is_detailed(180, NEAR, rule=none_close))

        wide = DetailRule(always_within_rings=1.0)
        self.assertTrue(self.is_detailed(180, FAR, rule=wide))

    def test_each_layer_uses_its_own_rule(self):
        self.assertIs(TrafficLayer.DETAIL_RULE, traffic_layer.TRAFFIC_DETAIL_RULE)
        self.assertIs(AirportLayer.DETAIL_RULE, airport_layer.AIRPORT_DETAIL_RULE)

        layer = TrafficLayer(make_canvas())
        layer.DETAIL_RULE = DetailRule(max_distance_rings=0.0)
        frame = make_frame()
        marker = ScopeMarker(distance=NEAR, bearing=0, color=[255, 0, 0])

        marker_set = layer.split_by_detail([marker], frame)

        self.assertEqual(marker_set.detailed, [])
        self.assertEqual(marker_set.simple, [marker])


class DetailFormulaTests(unittest.TestCase):
    """
    The whole rule can be swapped for any (marker, frame) -> score.
    """

    def setUp(self):
        self.frame = make_frame()
        self.near = ScopeMarker(distance=NEAR, bearing=0, color=[255, 0, 0], label="NEAR")
        self.far = ScopeMarker(distance=FAR, bearing=0, color=[255, 0, 0], label="FAR")

    def detailed_labels(self, layer):
        marker_set = layer.split_by_detail([self.near, self.far], self.frame)

        return [marker.label for marker in marker_set.detailed]

    def test_detail_rule_is_callable(self):
        self.assertGreater(DetailRule()(self.near, self.frame), 0.0)

    def test_true_and_false_still_work(self):
        class Booleans(TrafficLayer):
            def DETAIL_RULE(marker, frame): return marker.label == "FAR"

        self.assertEqual(self.detailed_labels(Booleans(make_canvas())), ["FAR"])

    def test_lambda_on_a_subclass(self):
        class OnlyNear(TrafficLayer):
            def DETAIL_RULE(marker, frame): return marker.distance < 1.0

        self.assertEqual(self.detailed_labels(OnlyNear(make_canvas())), ["NEAR"])

    def test_function_on_a_subclass(self):
        def only_far(marker, frame):
            return marker.distance > 1.0

        class OnlyFar(AirportLayer):
            DETAIL_RULE = only_far

        self.assertEqual(self.detailed_labels(OnlyFar(make_canvas())), ["FAR"])

    def test_staticmethod_on_a_subclass(self):
        class Everything(TrafficLayer):
            DETAIL_RULE = staticmethod(lambda marker, frame: True)

        self.assertEqual(self.detailed_labels(Everything(make_canvas())), ["NEAR", "FAR"])

    def test_lambda_on_one_instance(self):
        layer = TrafficLayer(make_canvas())
        layer.DETAIL_RULE = lambda marker, frame: False

        self.assertEqual(self.detailed_labels(layer), [])
        # Other layers keep the standard rule.
        self.assertEqual(self.detailed_labels(TrafficLayer(make_canvas())), ["NEAR", "FAR"])

    def test_formula_gets_marker_and_frame(self):
        seen = []

        class Spy(TrafficLayer):
            def DETAIL_RULE(marker, frame): return seen.append((marker, frame)) or False

        Spy(make_canvas()).split_by_detail([self.near], self.frame)

        self.assertEqual(seen, [(self.near, self.frame)])


class DetailScoringTests(unittest.TestCase):
    """
    The standard rule scores by closeness; layers keep the highest
    scores above their threshold, up to their cap.
    """

    def marker(self, distance, bearing=0, label=None):
        return ScopeMarker(distance=distance, bearing=bearing, color=[255, 0, 0], label=label)

    def test_closer_scores_higher(self):
        rule, frame = DetailRule(), make_frame()
        scores = [rule(self.marker(d), frame) for d in (0.1, 0.5, 1.0, 1.9)]

        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertAlmostEqual(scores[0], 1.0 - 0.1 / SCOPE_RANGE.center_ring_range)

    def test_ineligible_scores_zero(self):
        rule, frame = DetailRule(), make_frame()

        self.assertEqual(rule(self.marker(FAR, bearing=180), frame), 0.0)
        self.assertEqual(rule(self.marker(SCOPE_RANGE.center_ring_range + 0.1), frame), 0.0)

    def test_caps_keep_the_highest_scores_in_drawing_order(self):
        # Supplied far -> near, the way traffic is drawn.
        markers = [self.marker(d, label=str(d)) for d in (1.8, 1.4, 1.0, 0.6, 0.2)]

        class TopTwo(TrafficLayer):
            MAX_DETAILED = 2

        marker_set = TopTwo(make_canvas()).split_by_detail(markers, make_frame())

        self.assertEqual([m.label for m in marker_set.detailed], ["0.6", "0.2"])
        self.assertEqual([m.label for m in marker_set.simple], ["1.8", "1.4", "1.0"])

    def test_threshold(self):
        markers = [self.marker(d, label=str(d)) for d in (1.8, 1.0, 0.2)]

        class OnlyStrong(TrafficLayer):
            DETAIL_THRESHOLD = 0.5  # Closer than half the center ring

        marker_set = OnlyStrong(make_canvas()).split_by_detail(markers, make_frame())

        self.assertEqual([m.label for m in marker_set.detailed], ["0.2"])

    def test_ties_go_to_the_first_supplied(self):
        markers = [self.marker(1.0, label=label) for label in "ABC"]

        class FlatTopTwo(TrafficLayer):
            def DETAIL_RULE(marker, frame): return 0.5
            MAX_DETAILED = 2

        marker_set = FlatTopTwo(make_canvas()).split_by_detail(markers, make_frame())

        self.assertEqual([m.label for m in marker_set.detailed], ["A", "B"])

    def test_markers_that_will_not_be_drawn_do_not_use_up_the_cap(self):
        off_scope = self.marker(SCOPE_RANGE.max_ring_range + 1, label="OFF")
        on_scope = self.marker(1.0, label="ON")

        class EverythingTopOne(TrafficLayer):
            def DETAIL_RULE(marker, frame): return 1.0
            MAX_DETAILED = 1

        marker_set = EverythingTopOne(make_canvas()).split_by_detail(
            [off_scope, on_scope], make_frame()
        )

        self.assertEqual([m.label for m in marker_set.detailed], ["ON"])

    def test_layer_defaults(self):
        self.assertEqual(TrafficLayer.MAX_DETAILED, 20)
        self.assertEqual(AirportLayer.MAX_DETAILED, 10)
        self.assertEqual(TrafficLayer.DETAIL_THRESHOLD, 0.0)
        self.assertEqual(AirportLayer.DETAIL_THRESHOLD, 0.0)


class MarkerDrawingTests(unittest.TestCase):
    def setUp(self):
        renderer = marker_layer.drawing.renderer
        for name in ("polygon", "filled_circle", "segment", "segments"):
            patcher = patch.object(renderer, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_simple_markers_are_drawn_before_detailed(self):
        class FixedLayer(MarkerLayer):
            def get_markers(self, frame):
                return MarkerSet(
                    detailed=[ScopeMarker(1, 0, [1, 1, 1])],
                    simple=[ScopeMarker(1, 0, [2, 2, 2])],
                )

        FixedLayer(make_canvas()).render(make_frame())

        outline = list(marker_layer.MARKER_OUTLINE_COLOR)
        colors_drawn = [
            c.args[1] for c in self.filled_circle.call_args_list if c.args[1] != outline
        ]
        self.assertEqual(colors_drawn, [[2, 2, 2], [1, 1, 1]])

    def test_symbols_get_a_rim_drawn_under_them(self):
        canvas = make_canvas()
        layer = MarkerLayer(canvas)
        outline = list(marker_layer.MARKER_OUTLINE_COLOR)

        layer.__draw_symbol__(make_frame(canvas), ScopeMarker(1, 0, [255, 0, 0]), (10, 10))

        rim, dot = self.filled_circle.call_args_list
        self.assertEqual(rim.args[1], outline)
        self.assertEqual(dot.args[1], [255, 0, 0])
        self.assertGreater(rim.args[3], dot.args[3])

        layer.__draw_symbol__(make_frame(canvas), ScopeMarker(
            1, 0, [255, 0, 0], track=90), (10, 10))

        # A solid rim polygon around the arrow, then the arrow over it.
        rim, arrow = self.polygon.call_args_list
        self.assertEqual(rim.args[1], outline)
        self.assertEqual(arrow.args[1], [255, 0, 0])
        self.assertEqual(
            rim.args[2],
            marker_layer.get_outline_polygon(
                arrow.args[2],
                canvas.thin_line_width * marker_layer.MARKER_OUTLINE_WIDTH
                * marker_layer.ARROW_OUTLINE_FRACTION
                + marker_layer.OUTLINE_PIXEL_ALLOWANCE,
            ),
        )

    def test_rim_can_be_turned_off(self):
        with patch.object(marker_layer, "MARKER_OUTLINE_COLOR", None):
            MarkerLayer(make_canvas()).__draw_symbol__(
                make_frame(), ScopeMarker(1, 0, [255, 0, 0], track=90), (10, 10)
            )

        # Just the arrow; no rim.
        self.assertEqual([c.args[1] for c in self.polygon.call_args_list], [[255, 0, 0]])

    def test_markers_out_of_range_are_not_drawn(self):
        class FarLayer(MarkerLayer):
            def get_markers(self, frame):
                return MarkerSet(simple=[ScopeMarker(SCOPE_RANGE.max_ring_range + 1, 0, [1, 1, 1])])

        FarLayer(make_canvas()).render(make_frame())

        self.filled_circle.assert_not_called()

    def test_labels_stack_below_the_symbol(self):
        canvas = make_canvas()
        layer = MarkerLayer(canvas)
        marker = ScopeMarker(FAR, 0, [255, 0, 0], label="N1", sublabel="+5", label_color=[9, 9, 9])

        layer.__draw_labels__(make_frame(canvas), marker, (100, 100))

        draw = canvas.__host__.__render_centered_text__
        first_y = 100 + (canvas.no_direction_target_size << 2)
        self.assertEqual(draw.call_args_list[0].args[1:4], ("N1", [100, first_y], [9, 9, 9]))
        self.assertEqual(
            draw.call_args_list[1].args[1:3], ("+5", [100, first_y + canvas.font_half_height])
        )


class PredictionTests(unittest.TestCase):
    """
    Ported from the AdsbTopViewScope prediction tests.
    """

    def draw(self, points, projected, width=100, line_width=1):
        canvas = make_canvas(width=width, height=100, line_width=line_width)
        frame = make_frame(canvas)
        frame.project_position = Mock(side_effect=projected)
        marker = ScopeMarker(1, 0, [255, 0, 0], prediction_points=points)

        with patch.object(marker_layer.drawing.renderer, "segment") as segment:
            MarkerLayer(canvas).__draw_prediction__(frame, marker, (50, 50))

        return segment

    def test_clips_each_segment_of_turning_path(self):
        segment = self.draw(
            [(0.01, 0, 1000), (0.02, 0.01, 1000), (0.03, 0.02, 1000)],
            [(150, 50), (50, 80)],
            line_width=3,
        )

        self.assertEqual(segment.call_count, 2)
        self.assertEqual(
            segment.call_args_list[0], call(None, [255, 0, 0], [50, 50], [99, 50], width=3)
        )
        self.assertEqual(segment.call_args_list[1].args[2][0], 99)

    def test_skips_predictions_without_a_segment(self):
        for points in ([], [(0, 0, 1000)]):
            with self.subTest(points=points):
                self.draw(points, []).assert_not_called()

    def test_does_not_connect_across_invalid_points(self):
        segment = self.draw(
            [(0, 0, 1000), None, (1, 1, 1000), (2, 2, 1000)], [(30, 30), (40, 40)]
        )

        segment.assert_called_once_with(None, [255, 0, 0], [30, 30], [40, 40], width=2)

    def test_renders_closed_turn_with_offscreen_segments(self):
        segment = self.draw(
            [(0, 0, 1000), (0, 1, 1000), (1, 1, 1000), (0, 0, 1000)],
            [(-50, 50), (150, 50), (50, 50)],
        )

        self.assertEqual(segment.call_count, 3)
        self.assertEqual(
            segment.call_args_list[1], call(None, [255, 0, 0], [0, 50], [99, 50], width=2)
        )


class TrafficLayerTests(unittest.TestCase):
    def render(self, traffic, heading=0.0, **frame_options):
        # Threat levels are held for a few seconds per aircraft, and
        # every render's aircraft is "N123"; start each one fresh.
        traffic_threat.INSTANCE.clear()
        canvas = make_canvas()

        with patch.object(HudDataCache, "RELIABLE_TRAFFIC", traffic), patch.object(
            marker_layer.drawing.renderer, "polygon"
        ) as polygon, patch.object(marker_layer.drawing.renderer, "filled_circle"), patch.object(
            marker_layer.drawing.renderer, "segment"
        ) as segment, patch.object(marker_layer.drawing.renderer, "segments"):
            TrafficLayer(canvas).render(make_frame(canvas, heading=heading, **frame_options))

        return SimpleNamespace(
            labels=[c.args[1] for c in canvas.__host__.__render_centered_text__.call_args_list],
            polygon=polygon,
            segment=segment,
        )

    def test_traffic_just_across_north_is_labeled(self):
        drawn = self.render([traffic_at(offset(ORIGIN, 10, FAR))], heading=350)

        self.assertIn("N123", drawn.labels)

    def test_traffic_behind_is_not_labeled(self):
        drawn = self.render([traffic_at(offset(ORIGIN, 190, FAR))], heading=10)

        # Drawn (its rim, then the arrow)...
        self.assertEqual(drawn.polygon.call_count, 2)
        self.assertEqual(drawn.labels, [])

    def test_missing_compass_does_not_crash(self):
        drawn = self.render([traffic_at(offset(ORIGIN, 0, FAR))])

        self.assertIn("N123", drawn.labels)

    def test_predictions_only_for_detailed_traffic(self):
        target = offset(ORIGIN, 0, NEAR)
        path = {"points": [point(*target), point(*offset(ORIGIN, 0, NEAR + 0.2))]}

        inside = self.render([traffic_at(target, Prediction=path)])
        inside.segment.assert_called()

        outside_target = offset(ORIGIN, 0, SCOPE_RANGE.center_ring_range + 1)
        outside = self.render([traffic_at(outside_target, Prediction=path)])
        outside.segment.assert_not_called()

    def test_nothing_without_gps(self):
        drawn = self.render([traffic_at(offset(ORIGIN, 0, FAR))], gps_online=False)

        drawn.polygon.assert_not_called()

    def test_traffic_without_distance_is_skipped(self):
        traffic = traffic_at(offset(ORIGIN, 0, FAR))
        traffic.distance = None

        self.render([traffic]).polygon.assert_not_called()


class DistanceUnitTests(unittest.TestCase):
    """
    The rings are labeled in the user's units, so everything must be
    converted into them. Traffic (yards) always was; airports,
    breadcrumbs, and weather (statute miles) used to be drawn as if
    statute miles were the display units.
    """

    def test_conversions(self):
        knots = make_frame(display_units=units.NAUTICAL)
        metric = make_frame(display_units=units.METRIC)

        self.assertAlmostEqual(knots.statute_to_display(1.0), 0.868976, places=5)
        self.assertAlmostEqual(metric.statute_to_display(1.0), 1.609344, places=5)
        self.assertAlmostEqual(knots.display_to_statute(knots.statute_to_display(7.0)), 7.0)
        self.assertAlmostEqual(make_frame().statute_to_display(3.0), 3.0)

    def screen_positions_of_same_place(self, display_units):
        """
        An airport and a traffic target at the same spot, 2 statute
        miles away, should be drawn at the same pixel.
        """
        coordinates = offset(ORIGIN, 45, 2.0)
        scope_range = ScopeRange(5, 10, True)
        positions = {}

        for name, layer_type in (("airport", AirportLayer), ("traffic", TrafficLayer)):
            canvas = make_canvas()
            frame = make_frame(canvas, scope_range=scope_range, display_units=display_units)

            with patch.object(HudDataCache, "RELIABLE_TRAFFIC", [traffic_at(coordinates, Track=None)]), \
                    patch.object(AirportClient, "get_nearby_airports",
                                 return_value={"KTST": airport_at(coordinates)}), \
                    patch.object(AirportClient, "is_airport_data_valid", return_value=True), \
                    patch.object(marker_layer.drawing.renderer, "filled_circle") as filled_circle, \
                    patch.object(marker_layer.drawing.renderer, "polygon"):
                layer_type(canvas).render(frame)

            positions[name] = filled_circle.call_args.args[2]

        return positions

    def test_airports_and_traffic_agree_in_every_unit(self):
        for display_units in (units.STATUTE, units.NAUTICAL, units.METRIC):
            with self.subTest(display_units=display_units):
                positions = self.screen_positions_of_same_place(display_units)
                for axis in (0, 1):
                    self.assertAlmostEqual(
                        positions["airport"][axis], positions["traffic"][axis], delta=1
                    )

    def test_breadcrumbs_use_display_units(self):
        canvas = make_canvas()
        scope_range = ScopeRange(5, 10, True)
        frame = make_frame(canvas, scope_range=scope_range, display_units=units.NAUTICAL)
        crumb = offset(ORIGIN, 180, 4.0)
        trail = [[crumb, 1.0], [crumb, 1.0], [list(ORIGIN), 1.0]]

        with patch.object(breadcrumb_layer.breadcrumbs.INSTANCE, "get_trail", return_value=trail), \
                patch.object(breadcrumb_layer.drawing.renderer, "segment") as segment:
            BreadcrumbLayer(canvas).render(frame)

        drawn_y = segment.call_args_list[-1].args[2][1]
        expected_pixels = canvas.max_pixel_radius * (frame.distance_to(crumb) / 10)
        self.assertAlmostEqual(drawn_y - canvas.center[1], expected_pixels, delta=1)
        # 4 statute miles is ~3.48 nautical miles, not 4.
        self.assertAlmostEqual(frame.distance_to(crumb), 3.48, delta=0.02)

    def test_weather_is_scaled_from_statute_miles(self):
        canvas = make_canvas()
        layer = WeatherLayer(canvas)
        frame = make_frame(canvas, scope_range=ScopeRange(
            20, 50, True), display_units=units.NAUTICAL)
        bitmap = SimpleNamespace(
            lon_step=0.025, lat_step=1 / 60.0, surface=None,
            get_bitmap_position=lambda position: (0, 0),
        )

        with patch.object(weather_layer.drawing.renderer, "textured_disc") as disc:
            layer.__draw_reflectivity_bitmap__(frame, 0.0, bitmap)

        bin_height_pixels = disc.call_args.args[3][1]
        bin_height_miles = bitmap.lat_step * weather_layer.ReflectivityBitmap.MILES_PER_DEGREE
        pixels_per_statute_mile = canvas.max_pixel_radius / (50 / 0.868976)
        self.assertAlmostEqual(
            bin_height_pixels, bin_height_miles * pixels_per_statute_mile, places=3
        )

    def test_weather_fetches_far_enough_in_statute_miles(self):
        layer = WeatherLayer(make_canvas())
        frame = make_frame(display_units=units.NAUTICAL)

        with patch.object(weather_layer.NexradClient, "get_nexrad_in_range", return_value=[]) as fetch:
            layer.render(frame)

        # The furthest zoom (200) in nautical miles is ~230 statute miles.
        self.assertAlmostEqual(fetch.call_args.args[1], 200 / 0.868976, places=2)


if __name__ == "__main__":
    unittest.main()
