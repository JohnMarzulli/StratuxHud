import math
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from core_services import traffic_threat
    from core_services.traffic_threat import (
        REASON_ALTITUDE,
        REASON_GROUND,
        REASON_NO_DATA,
        REASON_PROXIMITY,
        REASON_TURNING,
        ThreatLevel,
        ThreatTracker,
        assess,
    )
    from data_sources import traffic_scenarios
    from data_sources.ahrs_data import AhrsData
    from data_sources.traffic import Traffic
    from views.scope_layers import ScopeMarker, ThreatsFirst
    from views.scope_layers.marker_layer import (
        THREAT_STYLES,
        ThreatStyle,
        get_outline_polygon,
        get_ring_progress,
        get_symbol_scale,
        get_threat_style,
        is_blink_on,
    )

ORIGIN = (44.0, -100.0)
FEET_PER_SM = 5280.0


def ownship(altitude=4500.0, track=0.0, speed=0.0, roll=0.0):
    ahrs = AhrsData()
    ahrs.position = list(ORIGIN)
    ahrs.gps_heading = track
    ahrs.groundspeed = speed
    ahrs.alt = altitude
    ahrs.vertical_speed = 0.0
    ahrs.roll = roll
    ahrs.gps_online = True

    return ahrs


def traffic_at(north_sm, east_sm=0.0, altitude=4500.0, gnss=True, **extra):
    """
    Stationary traffic the given distance north/east of ORIGIN.
    """
    north_nm = north_sm * traffic_threat.NM_PER_SM
    east_nm = east_sm * traffic_threat.NM_PER_SM
    report = {
        "displayName": "N1",
        "Lat": ORIGIN[0] + north_nm / 60.0,
        "Lng": ORIGIN[1] + east_nm / (60.0 * math.cos(math.radians(ORIGIN[0]))),
        "Track": 0.0,
        "Speed": 0.0,
        "Alt": altitude,
    }

    if gnss:
        report["GnssDiffFromBaroAlt"] = 0.0

    report.update(extra)
    report = {key: value for key, value in report.items() if value is not None}

    return Traffic("1", report)


def scenario_levels(name: str) -> list:
    """
    (seconds, assessment) once a second through the named scenario.
    """
    scenario = next(s for s in traffic_scenarios.SCENARIOS if s.name == name)
    results = []

    for seconds in range(int(scenario.duration_seconds) + 1):
        icao_address, report = traffic_scenarios.reports_at(scenario, seconds)[0]
        results.append((
            seconds,
            assess(Traffic(icao_address, report), traffic_scenarios.ownship_at(scenario, seconds)),
        ))

    return results


class ProximityTests(unittest.TestCase):
    def test_inside_the_critical_radius(self):
        result = assess(traffic_at(0.1), ownship())

        self.assertEqual(result.level, ThreatLevel.CRITICAL)
        self.assertEqual(result.reason, REASON_PROXIMITY)

    def test_inside_the_alert_radius(self):
        self.assertEqual(assess(traffic_at(0.2), ownship()).level, ThreatLevel.ALERT)

    def test_stationary_traffic_is_judged_on_the_bubbles_as_they_are(self):
        # Just outside the WARNING radius, and not moving: no growth.
        self.assertEqual(assess(traffic_at(0.55), ownship()).level, ThreatLevel.NONE)

    def test_far_away_is_no_threat(self):
        self.assertEqual(assess(traffic_at(3.0), ownship()).level, ThreatLevel.NONE)

    def test_close_but_far_above_is_filtered_by_altitude(self):
        result = assess(traffic_at(0.1, altitude=7500.0), ownship())

        self.assertEqual(result.level, ThreatLevel.NONE)
        self.assertEqual(result.reason, REASON_ALTITUDE)

    def test_no_altitude_is_judged_on_distance_alone(self):
        result = assess(traffic_at(0.1, altitude=None), ownship())

        self.assertEqual(result.level, ThreatLevel.CRITICAL)
        self.assertIsNone(result.vertical_feet)

    def test_pressure_altitude_only_gets_padding(self):
        # 1150 ft apart at 0.2 sm: outside ALERT's 1000 ft, unless the
        # altitude can't be confirmed as GPS altitude.
        confirmed = assess(traffic_at(0.2, altitude=5650.0), ownship())
        unconfirmed = assess(traffic_at(0.2, altitude=5650.0, gnss=False), ownship())

        self.assertLess(confirmed.level, ThreatLevel.ALERT)
        self.assertEqual(unconfirmed.level, ThreatLevel.ALERT)

    def test_pressure_altitude_is_converted_to_gnss(self):
        # Reads 500 ft low, but GnssDiffFromBaroAlt puts it at our altitude.
        result = assess(traffic_at(0.1, altitude=4000.0, GnssDiffFromBaroAlt=500.0), ownship())

        self.assertEqual(result.vertical_feet, 0.0)

    def test_ground_traffic_below_us_is_ignored(self):
        result = assess(traffic_at(0.1, altitude=2000.0, OnGround=True), ownship())

        self.assertEqual(result.reason, REASON_GROUND)

    def test_ground_traffic_is_a_threat_when_we_are_low(self):
        result = assess(traffic_at(0.1, altitude=4300.0, OnGround=True), ownship())

        self.assertEqual(result.level, ThreatLevel.CRITICAL)

    def test_no_gps_is_no_threat(self):
        own = ownship()
        own.gps_online = False

        self.assertEqual(assess(traffic_at(0.1), own).reason, REASON_NO_DATA)

    def test_unavailable_ownship_values_do_not_crash(self):
        own = ownship()
        own.alt = own.groundspeed = own.gps_heading = own.roll = "---"

        self.assertEqual(assess(traffic_at(0.1), own).level, ThreatLevel.CRITICAL)


class PredictionTests(unittest.TestCase):
    def test_closing_head_on_is_seen_ahead_of_time(self):
        # 1 sm apart, closing at 200 kt. The bubble grows by 15% of the
        # 0.74 sm they close, so they are "inside" about 12 s out.
        result = assess(traffic_at(1.0, Track=180.0, Speed=100.0), ownship(speed=100.0))

        self.assertEqual(result.level, ThreatLevel.CRITICAL)
        self.assertAlmostEqual(result.seconds, 12.0, delta=1.0)

    def test_look_ahead_limits_each_level(self):
        # Same closure from 4 sm: ALERT's bubble is about 51 s away,
        # past its 40 s look-ahead, so WARNING only.
        result = assess(traffic_at(4.0, Track=180.0, Speed=100.0), ownship(speed=100.0))

        self.assertEqual(result.level, ThreatLevel.WARNING)

    def test_vertical_closure_is_predicted(self):
        # Inside ALERT's radius, 1500 ft below, climbing at 1500 fpm.
        climbing = traffic_at(0.2, altitude=3000.0, Vvel=1500.0)
        level = traffic_at(0.2, altitude=3000.0)

        self.assertEqual(assess(climbing, ownship()).level, ThreatLevel.ALERT)
        self.assertEqual(assess(level, ownship()).level, ThreatLevel.NONE)

    def test_our_turn_is_predicted_from_bank(self):
        # Traffic off our right wing; we bank right toward it.
        target = traffic_at(0.0, east_sm=0.6)
        straight = assess(target, ownship(speed=100.0))
        turning = assess(target, ownship(speed=100.0, roll=30.0))

        self.assertEqual(straight.level, ThreatLevel.NONE)
        self.assertGreaterEqual(turning.level, ThreatLevel.ALERT)
        self.assertEqual(turning.reason, REASON_TURNING)

    def test_turn_rate_from_bank(self):
        # About 3 degrees per second at 100 kt and 15 degrees of bank.
        self.assertAlmostEqual(traffic_threat.get_turn_rate(ownship(speed=100.0, roll=15.3)), 3.0, delta=0.1)
        self.assertEqual(traffic_threat.get_turn_rate(ownship(speed=100.0, roll=3.0)), 0.0)


class ScenarioTests(unittest.TestCase):
    def assert_critical_by_encounter(self, name):
        scenario = next(s for s in traffic_scenarios.SCENARIOS if s.name == name)
        levels = scenario_levels(name)
        critical = [seconds for seconds, result in levels if result.level == ThreatLevel.CRITICAL]

        self.assertTrue(critical, name)
        self.assertLess(critical[0], scenario.encounter_seconds, name)

    def test_collision_scenarios_become_critical(self):
        for name in [
            "Head-on",
            "Converging from the right",
            "Overtaking slower traffic",
            "Being overtaken",
            "Pattern: turns final in front of us",
            "We turn into traffic",
            "Climbing up from below",
            "No altitude reported",
            "High pressure day (30.42)",
        ]:
            with self.subTest(name):
                self.assert_critical_by_encounter(name)

    def test_threats_clear_after_passing(self):
        levels = scenario_levels("Head-on")

        self.assertEqual(levels[-1][1].level, ThreatLevel.NONE)

    def test_our_turn_is_caught_by_the_turning_prediction(self):
        reasons = [result.reason for _, result in scenario_levels("We turn into traffic")]

        self.assertIn(REASON_TURNING, reasons)

    def test_non_threats_stay_low(self):
        for name, highest in [
            ("Parallel, same direction", ThreatLevel.WARNING),
            ("Close, but moving apart", ThreatLevel.NONE),
            ("Crossing 1500 ft above", ThreatLevel.NONE),
            ("On the ground below us", ThreatLevel.NONE),
        ]:
            with self.subTest(name):
                worst = max(result.level for _, result in scenario_levels(name))
                self.assertLessEqual(worst, highest)


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = ThreatTracker()
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def at(self, seconds):
        return self.start + timedelta(seconds=seconds)

    def test_level_rises_at_once_and_drops_after_the_hold(self):
        near, far = traffic_at(0.1), traffic_at(3.0)
        own = ownship()

        self.assertEqual(self.tracker.assess(far, own, self.at(0)).level, ThreatLevel.NONE)
        self.assertEqual(self.tracker.assess(near, own, self.at(1)).level, ThreatLevel.CRITICAL)
        self.assertEqual(self.tracker.assess(far, own, self.at(3)).level, ThreatLevel.CRITICAL)
        held_until = 1 + traffic_threat.LEVEL_HOLD_SECONDS
        self.assertEqual(self.tracker.assess(far, own, self.at(held_until)).level, ThreatLevel.NONE)

    def test_clear_forgets_everything(self):
        own = ownship()
        self.tracker.assess(traffic_at(0.1), own, self.at(0))
        self.tracker.clear()

        self.assertEqual(self.tracker.assess(traffic_at(3.0), own, self.at(1)).level, ThreatLevel.NONE)


class StyleTests(unittest.TestCase):
    def test_every_threat_level_has_a_look(self):
        self.assertEqual(get_threat_style(ThreatLevel.WARNING).outline_color, THREAT_STYLES[ThreatLevel.WARNING].outline_color)
        self.assertEqual(get_threat_style(ThreatLevel.NONE).outline_color, get_threat_style(99).outline_color)

    def test_blinking_alternates_on_and_off(self):
        style = ThreatStyle((255, 0, 0), flash_hz=4.0)

        self.assertTrue(is_blink_on(style, 0.0))
        self.assertFalse(is_blink_on(style, 0.15))
        self.assertTrue(is_blink_on(style, 0.25))
        self.assertTrue(is_blink_on(ThreatStyle((255, 0, 0)), 0.15))

    def test_pulse_grows_and_shrinks(self):
        style = ThreatStyle((255, 0, 0), scale=1.5, pulse_hz=2.0, pulse_scale=0.5)

        self.assertAlmostEqual(get_symbol_scale(style, 0.0), 1.5)
        self.assertAlmostEqual(get_symbol_scale(style, 0.25), 2.0)
        self.assertAlmostEqual(get_symbol_scale(style, 0.5), 1.5)

    def test_ring_leaves_at_the_peak_of_each_pulse(self):
        style = ThreatStyle((255, 0, 0), pulse_hz=2.0, pulse_scale=0.5, ring_scale=5.0)

        self.assertAlmostEqual(get_ring_progress(style, 0.25), 0.0)  # Peak
        self.assertAlmostEqual(get_ring_progress(style, 0.5), 0.5)
        self.assertIsNone(get_ring_progress(ThreatStyle((255, 0, 0), pulse_hz=2.0), 0.25))


def distance_to_segment(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    along = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)
    along = max(0.0, min(1.0, along))

    return math.hypot(point[0] - (start[0] + dx * along), point[1] - (start[1] + dy * along))


class OutlinePolygonTests(unittest.TestCase):
    ARROW = [[-5, 10], [0, -10], [5, 10]]  # Narrow tip at the top

    def test_every_edge_is_pushed_out_by_the_width(self):
        square = [[0, 0], [10, 0], [10, 10], [0, 10]]
        outline = get_outline_polygon(square, 2)

        self.assertEqual(outline, [[-2, -2], [12, -2], [12, 12], [-2, 12]])

    def test_sharp_tip_is_clipped_not_a_spike(self):
        outline = get_outline_polygon(self.ARROW, 2, miter_limit=2.0)
        topmost = min(point[1] for point in outline)

        # Cut square, 2 * width above the tip.
        self.assertEqual(len(outline), 4)
        self.assertAlmostEqual(topmost, -14.0)

    def test_the_rim_is_full_width_all_the_way_round(self):
        # Every point on the arrow's edges, tip and corners included, is
        # at least the rim width from the outside of the outline.
        outline = get_outline_polygon(self.ARROW, 2)
        outline_edges = list(zip(outline, outline[1:] + outline[:1]))

        for start, end in zip(self.ARROW, self.ARROW[1:] + self.ARROW[:1]):
            for step in range(11):
                point = [start[0] + (end[0] - start[0]) * step / 10, start[1] + (end[1] - start[1]) * step / 10]
                nearest = min(distance_to_segment(point, *edge) for edge in outline_edges)
                self.assertGreaterEqual(nearest, 2.0 - 1e-9, point)

    def test_winding_order_does_not_matter(self):
        clockwise = get_outline_polygon(self.ARROW, 2)
        counter_clockwise = get_outline_polygon(list(reversed(self.ARROW)), 2)

        self.assertEqual(
            sorted(map(tuple, clockwise)), sorted(map(tuple, counter_clockwise))
        )


class ThreatsFirstTests(unittest.TestCase):
    def test_threats_outrank_everything_worst_first(self):
        rule = ThreatsFirst(lambda marker, frame: 0.9)
        frame = SimpleNamespace()

        none = rule(ScopeMarker(1, 0, [0, 0, 0]), frame)
        warning = rule(ScopeMarker(1, 0, [0, 0, 0], threat_level=ThreatLevel.WARNING), frame)
        critical = rule(ScopeMarker(1, 0, [0, 0, 0], threat_level=ThreatLevel.CRITICAL), frame)

        self.assertEqual(none, 0.9)
        self.assertGreater(warning, none)
        self.assertGreater(critical, warning)


if __name__ == "__main__":
    unittest.main()
