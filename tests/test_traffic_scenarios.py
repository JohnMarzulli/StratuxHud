import math
import unittest
from unittest.mock import Mock, patch

with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from data_sources import traffic_scenarios
    from data_sources.ahrs_data import AhrsData
    from data_sources.traffic import Traffic
    from data_sources.traffic_scenarios import (
        Flight,
        Leg,
        Scenario,
        get_roll,
        ownship_at,
        reports_at,
    )


def separation_nm(scenario: Scenario, seconds: float, index: int = 0) -> float:
    own = scenario.ownship.state_at(seconds)
    other = scenario.traffic[index].state_at(seconds)

    return math.hypot(other.east - own.east, other.north - own.north)


def scenario_named(name: str) -> Scenario:
    return next(
        scenario for scenario in traffic_scenarios.SCENARIOS if scenario.name == name
    )


class FlightTests(unittest.TestCase):
    def test_straight_flight_covers_speed_times_time(self):
        flight = Flight("A", track=90.0, speed=120.0)
        state = flight.state_at(60.0)

        self.assertAlmostEqual(state.east, 2.0)
        self.assertAlmostEqual(state.north, 0.0)

    def test_full_circle_returns_to_the_start(self):
        flight = Flight("A", legs=(Leg(turn_rate=3.0),))
        state = flight.state_at(120.0)

        self.assertAlmostEqual(state.east, 0.0, places=9)
        self.assertAlmostEqual(state.north, 0.0, places=9)
        self.assertAlmostEqual(state.track % 360.0, flight.track, places=6)

    def test_legs_are_flown_in_order(self):
        flight = Flight(
            "A", track=0.0, speed=60.0,
            legs=(Leg(seconds=30.0, turn_rate=3.0, vertical_speed=600.0), Leg()),
        )
        state = flight.state_at(90.0)

        self.assertAlmostEqual(state.track, 90.0)
        self.assertEqual(state.turn_rate, 0.0)
        self.assertAlmostEqual(state.altitude, flight.altitude + 300.0)

    def test_end_of_a_leg_reports_the_next_legs_rates(self):
        flight = Flight("A", legs=(Leg(seconds=10.0, turn_rate=3.0), Leg()))

        self.assertEqual(flight.state_at(10.0).turn_rate, 0.0)
        self.assertEqual(flight.state_at(9.0).turn_rate, 3.0)

    def test_relative_to_uses_our_nose_as_zero(self):
        ownship = Flight("OWN", track=90.0)
        other = Flight.relative_to(ownship, "B", clock=90.0, range_nm=1.0, relative_track=180.0)

        self.assertAlmostEqual(other.east, 0.0)
        self.assertAlmostEqual(other.north, -1.0)
        self.assertAlmostEqual(other.track, 270.0)

    def test_meeting_arrives_at_our_position(self):
        ownship = Flight("OWN")
        other = Flight.meeting(ownship, "B", 80.0, 135.0, speed=140.0)
        own_then, other_then = ownship.state_at(80.0), other.state_at(80.0)

        self.assertAlmostEqual(other_then.east, own_then.east)
        self.assertAlmostEqual(other_then.north, own_then.north)
        self.assertAlmostEqual(other_then.altitude, own_then.altitude)

    def test_meeting_allows_for_both_aircrafts_turns(self):
        ownship = Flight("OWN", legs=(Leg(seconds=20.0), Leg(seconds=30.0, turn_rate=-3.0), Leg()))
        other = Flight.meeting(
            ownship, "B", 90.0, 45.0,
            legs=(Leg(seconds=50.0, vertical_speed=-600.0), Leg(turn_rate=2.0)),
        )
        scenario = Scenario("x", "", ownship, (other,))

        self.assertAlmostEqual(separation_nm(scenario, 90.0), 0.0, places=9)
        self.assertGreater(separation_nm(scenario, 0.0), 1.0)

    def test_meeting_miss_distance_and_height(self):
        ownship = Flight("OWN", track=0.0)
        other = Flight.meeting(
            ownship, "B", 60.0, 90.0, miss_clock=90.0, miss_nm=0.5, miss_feet=700.0,
        )
        own_then, other_then = ownship.state_at(60.0), other.state_at(60.0)

        self.assertAlmostEqual(other_then.east - own_then.east, 0.5)
        self.assertAlmostEqual(other_then.north - own_then.north, 0.0)
        self.assertAlmostEqual(other_then.altitude - own_then.altitude, 700.0)


class ScenarioTests(unittest.TestCase):
    def test_every_scenario_produces_reports_the_hud_can_parse(self):
        for scenario in traffic_scenarios.SCENARIOS:
            for seconds in (0.0, scenario.duration_seconds / 2, scenario.duration_seconds):
                for icao_address, report in reports_at(scenario, seconds):
                    parsed = Traffic(icao_address, report)

                    self.assertIsNotNone(parsed.distance, scenario.name)
                    self.assertIsNotNone(parsed.bearing, scenario.name)
                    self.assertTrue(parsed.get_prediction_points(), scenario.name)

                self.assertIsInstance(ownship_at(scenario, seconds), AhrsData)

    def test_encounters_happen_when_they_say(self):
        for name in [
            "Head-on",
            "Converging from the right",
            "Pattern: turns final in front of us",
            "We turn into traffic",
            "Climbing up from below",
            "No altitude reported",
            "High pressure day (30.42)",
        ]:
            scenario = scenario_named(name)
            encounter = scenario.encounter_seconds

            self.assertAlmostEqual(separation_nm(scenario, encounter), 0.0, places=6, msg=name)
            self.assertGreater(separation_nm(scenario, 0.0), 1.0, name)

    def test_parallel_traffic_stays_put(self):
        scenario = scenario_named("Parallel, same direction")

        for seconds in (0.0, 60.0, scenario.duration_seconds):
            self.assertAlmostEqual(separation_nm(scenario, seconds), 0.5)

    def test_climber_reaches_our_altitude_at_the_encounter(self):
        scenario = scenario_named("Climbing up from below")
        encounter = scenario.encounter_seconds
        own, other = scenario.ownship, scenario.traffic[0]

        self.assertAlmostEqual(other.state_at(0.0).altitude, own.altitude - traffic_scenarios.CLIMB_FROM_BELOW_FEET)
        self.assertAlmostEqual(other.state_at(encounter).altitude, own.state_at(encounter).altitude)

    def test_busy_airport_is_the_same_every_time(self):
        first = traffic_scenarios.__busy_airport__()
        second = traffic_scenarios.__busy_airport__()

        self.assertEqual(first, second)
        self.assertEqual(len(first.traffic), 25)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.ownship = Flight("OWN", track=0.0)

    def report_for(self, other: Flight, seconds: float = 0.0, **options) -> dict:
        scenario = Scenario("x", "", self.ownship, (other,), **options)

        return reports_at(scenario, seconds)[0][1]

    def test_distance_is_meters_and_bearing_is_true(self):
        other = Flight.relative_to(self.ownship, "B", clock=90.0, range_nm=2.0)
        report = self.report_for(other)

        self.assertAlmostEqual(report["Distance"], 2.0 * 1852.0)
        self.assertAlmostEqual(report["Bearing"], 90.0)

    def test_pressure_altitude_offset(self):
        other = Flight.relative_to(self.ownship, "B", clock=0.0, range_nm=1.0)
        report = self.report_for(other, pressure_altitude_offset=-500.0)

        self.assertAlmostEqual(report["Alt"], self.ownship.altitude - 500.0)
        self.assertEqual(report["GnssDiffFromBaroAlt"], 500.0)
        self.assertFalse(report["AltIsGNSS"])

    def test_no_altitude_is_left_out(self):
        other = Flight.relative_to(self.ownship, "B", clock=0.0,
                                   range_nm=1.0, reports_altitude=False)
        report = self.report_for(other)
        parsed = Traffic("1", report)

        self.assertNotIn("Alt", report)
        self.assertIsNone(parsed.altitude)
        self.assertEqual(parsed.get_altitude_delta_text(AhrsData()), "UNK")

    def test_straight_prediction_matches_traffic_to_hud(self):
        other = Flight.relative_to(self.ownship, "B", clock=0.0, range_nm=1.0, speed=120.0)
        prediction = self.report_for(other)["Prediction"]

        self.assertEqual(prediction["type"], "straight")
        self.assertEqual([point["secondsAhead"] for point in prediction["points"]], [0.0, 60.0])

    def test_turning_prediction_follows_the_arc(self):
        other = Flight.relative_to(
            self.ownship, "B", clock=0.0, range_nm=1.0, legs=(Leg(turn_rate=3.0, vertical_speed=500.0),),
        )
        report = self.report_for(other)
        prediction = report["Prediction"]
        last = prediction["points"][-1]
        actual = other.state_at(60.0)

        self.assertEqual(prediction["type"], "turning")
        self.assertEqual(len(prediction["points"]), 19)  # 180 degrees in 10 degree pieces
        self.assertAlmostEqual(last["Track"], actual.track)
        self.assertAlmostEqual(last["Alt"], report["Alt"] + 500.0)

    def test_slow_turns_are_predicted_straight(self):
        other = Flight.relative_to(
            self.ownship, "B", clock=0.0, range_nm=1.0, legs=(Leg(turn_rate=0.5),),
        )

        self.assertEqual(self.report_for(other)["Prediction"]["type"], "straight")


class OwnshipTests(unittest.TestCase):
    def test_standard_rate_turn_bank(self):
        # About 15 degrees of bank for a standard rate turn at 100 kt.
        state = Flight("OWN", legs=(Leg(turn_rate=3.0),)).state_at(0.0)

        self.assertAlmostEqual(get_roll(state), 15.3, delta=0.5)

    def test_ownship_follows_its_script(self):
        scenario = scenario_named("We turn into traffic")

        self.assertEqual(ownship_at(scenario, 1.0).roll, 0.0)
        self.assertGreater(ownship_at(scenario, 20.0).roll, 10.0)
        self.assertAlmostEqual(
            ownship_at(scenario, 40.0).gps_heading, scenario.ownship.track + 90.0
        )


if __name__ == "__main__":
    unittest.main()
