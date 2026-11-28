"""
Scripted traffic encounters, for seeing (and testing) how the HUD
shows traffic that could be a collision hazard.

A scenario is us plus a handful of other aircraft, each flying a
simple script of legs (straight, turning, climbing...). Positions are
worked out exactly for any time, so a scenario can be played, paused,
and stepped backwards and forwards.

At any time a scenario produces:

    ownship_at(scenario, t)   AhrsData for us, as the AHRS would give it
    reports_at(scenario, t)   Traffic reports, as TrafficToHud gives them
                              (Stratux fields plus its "Prediction")

Reports go in through the same TrafficManager as real traffic, so
everything downstream (parsing, the scope, the threat logic) runs
unchanged.

Scenarios are authored relative to our own aircraft, so they read
like the encounter they describe:

    Flight.meeting(ownship, at_seconds=100, relative_track=180)
        Head-on: at t=100 it is exactly where we are.

    Flight.relative_to(ownship, clock=90, range_nm=0.5)
        Starts half a mile off our right wing.

Units: nautical miles, knots, feet, feet per minute, degrees true.
Turn rates are degrees per second, positive to the right.
"""

import math
import random
from dataclasses import dataclass, field, replace
from typing import Optional

from common_utils import fast_math, geo_math
from data_sources.ahrs_data import AhrsData

# Where the scenarios are flown. Far from anything in the example
# airport/weather data so nothing else clutters the scope.
ORIGIN = (44.0, -100.0)

METERS_PER_NM = 1852.0
METERS_PER_SECOND_PER_KNOT = 0.514444
GRAVITY = 9.80665

# How far ahead TrafficToHud predicts paths by default, and the turn
# rate below which it calls a target "straight".
PREDICTION_SECONDS = 60.0
STRAIGHT_TURN_RATE = 1.0
MAX_DEGREES_PER_ARC_SEGMENT = 10.0

# Stratux reports "Distance" in meters. (The HUD treats the value as
# yards; that is ~9% short, and this keeps that behavior visible.)
DISTANCE_UNITS_PER_NM = METERS_PER_NM

FIRST_ICAO_ADDRESS = 0xA00001

DEFAULT_TRACK = 30.0
DEFAULT_ALTITUDE = 4500.0
DEFAULT_SPEED = 100.0
# Encounters happen soon after the start, so there is little
# waiting; at our closing speeds they start 1-3 miles apart.
DEFAULT_ENCOUNTER_SECONDS = 45.0
# How long a scenario keeps going after its encounter.
SECONDS_AFTER_ENCOUNTER = 15.0
DEFAULT_DURATION_SECONDS = DEFAULT_ENCOUNTER_SECONDS + SECONDS_AFTER_ENCOUNTER

# How far below the climbing traffic starts.
CLIMB_FROM_BELOW_FEET = 1000.0


@dataclass(frozen=True)
class Leg:
    """
    One piece of a flight's script. The last leg goes on forever.
    """

    seconds: float = math.inf
    turn_rate: float = 0.0  # Degrees per second, positive is right
    vertical_speed: float = 0.0  # Feet per minute, positive is up


STRAIGHT_AND_LEVEL = (Leg(),)


@dataclass(frozen=True)
class FlightState:
    """
    Where an aircraft is, and what it is doing, at one moment.
    """

    east: float  # NM from the scenario origin
    north: float  # NM from the scenario origin
    altitude: float
    track: float
    speed: float
    turn_rate: float
    vertical_speed: float


def __fly_leg__(state: FlightState, leg: Leg, seconds: float) -> FlightState:
    """
    Flies a constant turn rate / vertical speed for the given time.

    For turn rate w (radians/s), speed v and starting track h0:
        east(t)  = (v/w) * (cos(h0) - cos(h0 + wt))
        north(t) = (v/w) * (sin(h0 + wt) - sin(h0))
    which becomes a straight line as w goes to zero.
    """
    nm_per_second = state.speed / 3600.0
    start_track = math.radians(state.track)
    turn_rate = math.radians(leg.turn_rate)

    if abs(turn_rate) < 1e-9:
        distance = nm_per_second * seconds
        east = distance * math.sin(start_track)
        north = distance * math.cos(start_track)
    else:
        radius = nm_per_second / turn_rate
        end_track = start_track + (turn_rate * seconds)
        east = radius * (math.cos(start_track) - math.cos(end_track))
        north = radius * (math.sin(end_track) - math.sin(start_track))

    return FlightState(
        east=state.east + east,
        north=state.north + north,
        altitude=state.altitude + (leg.vertical_speed / 60.0) * seconds,
        track=fast_math.wrap_degrees(state.track + leg.turn_rate * seconds),
        speed=state.speed,
        turn_rate=leg.turn_rate,
        vertical_speed=leg.vertical_speed,
    )


@dataclass(frozen=True)
class Flight:
    """
    An aircraft's starting state and its script of legs.
    """

    tail: str
    east: float = 0.0
    north: float = 0.0
    altitude: float = DEFAULT_ALTITUDE
    track: float = DEFAULT_TRACK
    speed: float = DEFAULT_SPEED
    legs: tuple = STRAIGHT_AND_LEVEL
    on_ground: bool = False
    # False sends no altitude, like a transponder without Mode C.
    reports_altitude: bool = True

    def state_at(self, seconds: float) -> FlightState:
        """
        Where this aircraft is the given number of seconds into the
        scenario (negative times fly the first leg backwards).
        """
        state = FlightState(
            self.east, self.north, self.altitude, self.track, self.speed,
            self.legs[0].turn_rate, self.legs[0].vertical_speed,
        )

        if seconds <= 0.0:
            return __fly_leg__(state, self.legs[0], seconds)

        remaining = seconds

        for index, leg in enumerate(self.legs):
            is_last = index == len(self.legs) - 1
            leg_seconds = remaining if is_last else min(remaining, leg.seconds)
            state = __fly_leg__(state, leg, leg_seconds)
            remaining -= leg_seconds

            if remaining <= 0.0:
                if not is_last and leg_seconds >= leg.seconds:
                    # Exactly at the end of this leg: report the next
                    # leg's rates, since that is what it is doing now.
                    following = self.legs[index + 1]
                    state = replace(
                        state,
                        turn_rate=following.turn_rate,
                        vertical_speed=following.vertical_speed,
                    )

                break

        return state

    @staticmethod
    def relative_to(
        ownship: "Flight",
        tail: str,
        clock: float,
        range_nm: float,
        altitude_offset: float = 0.0,
        relative_track: float = 0.0,
        speed: float = DEFAULT_SPEED,
        legs: tuple = STRAIGHT_AND_LEVEL,
        **options,
    ) -> "Flight":
        """
        Starts at a bearing (degrees off our nose, 90 is our right
        wing) and range from us, with a track relative to ours.
        """
        bearing = math.radians(ownship.track + clock)

        return Flight(
            tail=tail,
            east=ownship.east + range_nm * math.sin(bearing),
            north=ownship.north + range_nm * math.cos(bearing),
            altitude=ownship.altitude + altitude_offset,
            track=fast_math.wrap_degrees(ownship.track + relative_track),
            speed=speed,
            legs=legs,
            **options,
        )

    @staticmethod
    def meeting(
        ownship: "Flight",
        tail: str,
        at_seconds: float,
        relative_track: float,
        speed: float = DEFAULT_SPEED,
        miss_clock: float = 0.0,
        miss_nm: float = 0.0,
        miss_feet: float = 0.0,
        legs: tuple = STRAIGHT_AND_LEVEL,
        **options,
    ) -> "Flight":
        """
        Placed so that, flying its legs, it is miss_nm from us (at
        miss_clock off our nose at that moment) and miss_feet above
        us at at_seconds. With no miss it flies right into us.

        relative_track is its STARTING track, relative to our
        starting track; legs (turns, climbs) are flown from there,
        and both aircraft's turns are allowed for.
        """
        own_then = ownship.state_at(at_seconds)
        miss_bearing = math.radians(own_then.track + miss_clock)

        target_east = own_then.east + miss_nm * math.sin(miss_bearing)
        target_north = own_then.north + miss_nm * math.cos(miss_bearing)
        target_altitude = own_then.altitude + miss_feet

        # How far it moves doesn't depend on where it starts, so fly
        # it from zero and shift the start by what is left over.
        unplaced = Flight(
            tail=tail,
            east=0.0,
            north=0.0,
            altitude=0.0,
            track=fast_math.wrap_degrees(ownship.track + relative_track),
            speed=speed,
            legs=legs,
            **options,
        )
        moved = unplaced.state_at(at_seconds)

        return replace(
            unplaced,
            east=target_east - moved.east,
            north=target_north - moved.north,
            altitude=target_altitude - moved.altitude,
        )


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    ownship: Flight
    traffic: tuple
    duration_seconds: float = DEFAULT_DURATION_SECONDS
    # When the encounter happens, to show "T-minus". None if there is
    # no single moment.
    encounter_seconds: Optional[float] = DEFAULT_ENCOUNTER_SECONDS
    # Traffic reports pressure altitude; we use GPS altitude. Positive
    # means the traffic's reported altitude reads this much higher
    # than its real altitude (a low pressure day).
    pressure_altitude_offset: float = 0.0
    tags: tuple = field(default_factory=tuple)


# -- Positions -------------------------------------------------------------


def __to_latitude_longitude__(east: float, north: float) -> tuple:
    """
    Flat earth offset from the origin. Accurate for the few miles a
    scenario covers.
    """
    latitude = ORIGIN[0] + math.degrees(north / geo_math.EARTH_RADIUS_NAUTICAL_MILES)
    longitude = ORIGIN[1] + math.degrees(
        east / (geo_math.EARTH_RADIUS_NAUTICAL_MILES * math.cos(math.radians(ORIGIN[0])))
    )

    return latitude, longitude


def get_roll(state: FlightState) -> float:
    """
    The bank angle for a coordinated turn: tan(bank) = v * w / g.
    """
    velocity = state.speed * METERS_PER_SECOND_PER_KNOT
    turn_rate = math.radians(state.turn_rate)

    return math.degrees(math.atan2(velocity * turn_rate, GRAVITY))


def ownship_at(scenario: Scenario, seconds: float) -> AhrsData:
    """
    Our own AHRS/GPS data at the given time.
    """
    state = scenario.ownship.state_at(seconds)
    ahrs = AhrsData()
    ahrs.position = list(__to_latitude_longitude__(state.east, state.north))
    ahrs.gps_heading = state.track
    ahrs.compass_heading = state.track
    ahrs.groundspeed = state.speed
    ahrs.airspeed = state.speed
    ahrs.alt = state.altitude
    ahrs.vertical_speed = state.vertical_speed
    ahrs.roll = get_roll(state)
    ahrs.pitch = 0.0
    ahrs.gps_online = True

    return ahrs


def __prediction_point__(state: FlightState, seconds_ahead: float, altitude) -> dict:
    latitude, longitude = __to_latitude_longitude__(state.east, state.north)

    return {
        "secondsAhead": seconds_ahead,
        "Lat": latitude,
        "Lng": longitude,
        "Alt": altitude,
        "Track": state.track,
    }


def get_prediction(state: FlightState, reported_altitude) -> dict:
    """
    The "Prediction" TrafficToHud adds to each target (see its
    flight-path-prediction.ts): two points when straight, an arc of
    points when turning, never more than a full circle.

    It assumes the current turn rate and vertical speed hold, which
    is exactly what makes a pattern turn look surprising.
    """
    turn_rate = state.turn_rate if abs(state.turn_rate) >= STRAIGHT_TURN_RATE else 0.0
    holding = Leg(turn_rate=turn_rate, vertical_speed=state.vertical_speed)

    if turn_rate == 0.0:
        seconds_ahead = PREDICTION_SECONDS
        times = [0.0, seconds_ahead]
    else:
        seconds_ahead = min(PREDICTION_SECONDS, 360.0 / abs(turn_rate))
        sweep = abs(turn_rate * seconds_ahead)
        segments = max(1, math.ceil(sweep / MAX_DEGREES_PER_ARC_SEGMENT))
        times = [seconds_ahead * index / segments for index in range(segments + 1)]

    points = []

    for time in times:
        ahead = __fly_leg__(state, holding, time)
        altitude = (
            None
            if reported_altitude is None
            else reported_altitude + (state.vertical_speed / 60.0) * time
        )
        points.append(__prediction_point__(ahead, time, altitude))

    return {
        "type": "straight" if turn_rate == 0.0 else "turning",
        "secondsAhead": seconds_ahead,
        "speedKnots": state.speed,
        "turnRateDegreesPerSecond": turn_rate,
        "points": points,
    }


def get_icao_address(index: int) -> str:
    return str(FIRST_ICAO_ADDRESS + index)


def reports_at(scenario: Scenario, seconds: float) -> list:
    """
    (ICAO address, report) for every aircraft at the given time, in
    the shape TrafficToHud's /Traffic/Reliable gives them.
    """
    own = scenario.ownship.state_at(seconds)
    reports = []

    for index, flight in enumerate(scenario.traffic):
        state = flight.state_at(seconds)
        east = state.east - own.east
        north = state.north - own.north
        latitude, longitude = __to_latitude_longitude__(state.east, state.north)
        icao_address = get_icao_address(index)
        reported_altitude = (
            state.altitude + scenario.pressure_altitude_offset
            if flight.reports_altitude
            else None
        )

        report = {
            "Icao_addr": int(icao_address),
            "Tail": flight.tail,
            "Reg": flight.tail,
            "displayName": flight.tail,
            "OnGround": flight.on_ground,
            "Position_valid": True,
            "Lat": latitude,
            "Lng": longitude,
            "Track": state.track,
            "Speed": state.speed,
            "Speed_valid": True,
            "Vvel": state.vertical_speed,
            "AltIsGNSS": False,
            "GnssDiffFromBaroAlt": -scenario.pressure_altitude_offset,
            "BearingDist_valid": True,
            "Bearing": fast_math.wrap_degrees(math.degrees(math.atan2(east, north))),
            "Distance": math.hypot(east, north) * DISTANCE_UNITS_PER_NM,
            "Age": 0.1,
            "AgeLastAlt": 0.1,
            "ExtrapolatedPosition": False,
            "Prediction": get_prediction(state, reported_altitude),
        }

        if reported_altitude is not None:
            report["Alt"] = reported_altitude

        reports.append((icao_address, report))

    return reports


# -- The scenarios -----------------------------------------------------------

# Encounter times are picked so the traffic starts on screen at the
# 1/2 SM zoom, which shows about 2 SM ahead, 2.2 SM to the sides,
# and only 0.7 SM behind.


def __timing__(encounter_seconds: float) -> dict:
    return {
        "encounter_seconds": encounter_seconds,
        "duration_seconds": encounter_seconds + SECONDS_AFTER_ENCOUNTER,
    }


def __head_on__() -> Scenario:
    encounter = 28.0
    ownship = Flight("OWN")

    return Scenario(
        "Head-on",
        "Same altitude, opposite direction, 110 kt.",
        ownship,
        (Flight.meeting(ownship, "N1HO", encounter, 180.0, speed=110.0),),
        **__timing__(encounter),
        tags=("straight",),
    )


def __converging_right__() -> Scenario:
    encounter = 40.0
    ownship = Flight("OWN")

    return Scenario(
        "Converging from the right",
        "Crossing at 90 degrees from our right, same altitude.",
        ownship,
        (Flight.meeting(ownship, "N2CR", encounter, -90.0),),
        **__timing__(encounter),
        tags=("straight",),
    )


def __overtaking__() -> Scenario:
    ownship = Flight("OWN", speed=110.0)

    return Scenario(
        "Overtaking slower traffic",
        "Same track, 70 kt ahead of us, we pass 0.05 nm to its left.",
        ownship,
        (Flight.meeting(
            ownship, "N3OT", DEFAULT_ENCOUNTER_SECONDS, 0.0, speed=70.0,
            miss_clock=90.0, miss_nm=0.05,
        ),),
        tags=("straight",),
    )


def __being_overtaken__() -> Scenario:
    encounter = 30.0
    ownship = Flight("OWN", speed=90.0)

    return Scenario(
        "Being overtaken",
        "Same track, 160 kt from behind, passes 0.05 nm off our left.",
        ownship,
        (Flight.meeting(
            ownship, "N4BO", encounter, 0.0, speed=160.0,
            miss_clock=-90.0, miss_nm=0.05,
        ),),
        **__timing__(encounter),
        tags=("straight",),
    )


def __parallel__() -> Scenario:
    ownship = Flight("OWN")

    return Scenario(
        "Parallel, same direction",
        "Half a mile off our right wing, same speed and altitude.",
        ownship,
        (Flight.relative_to(ownship, "N5PL", clock=90.0, range_nm=0.5),),
        encounter_seconds=None,
        tags=("no-threat",),
    )


def __diverging__() -> Scenario:
    ownship = Flight("OWN")

    return Scenario(
        "Close, but moving apart",
        "Starts 0.6 nm ahead-right, heading 60 degrees away from us.",
        ownship,
        (Flight.relative_to(
            ownship, "N6DV", clock=45.0, range_nm=0.6, relative_track=60.0, speed=120.0,
        ),),
        duration_seconds=40.0,
        encounter_seconds=None,
        tags=("no-threat",),
    )


def __pattern_turn_to_final__() -> Scenario:
    # We are on a long final, descending. They are on base, then turn
    # onto final right in front of us.
    final = Leg(vertical_speed=-500.0)
    ownship = Flight("OWN", altitude=1500.0, speed=90.0, legs=(final,))
    base_then_final = (
        Leg(seconds=DEFAULT_ENCOUNTER_SECONDS - 30.0, vertical_speed=-500.0),
        Leg(seconds=30.0, turn_rate=3.0, vertical_speed=-500.0),
        Leg(vertical_speed=-500.0),
    )

    return Scenario(
        "Pattern: turns final in front of us",
        "They fly base toward our final, then turn onto final just ahead of us.",
        ownship,
        (Flight.meeting(
            ownship, "N7PT", DEFAULT_ENCOUNTER_SECONDS, -90.0, speed=75.0,
            legs=base_then_final,
        ),),
        tags=("turning",),
    )


def __ownship_turning__() -> Scenario:
    encounter = 40.0
    ownship = Flight(
        "OWN",
        legs=(Leg(seconds=2.0), Leg(seconds=30.0, turn_rate=3.0), Leg()),
    )

    return Scenario(
        "We turn into traffic",
        "We turn right 90 degrees; they fly straight. Head-on after our turn.",
        ownship,
        (Flight.meeting(ownship, "N8OT", encounter, 270.0),),
        **__timing__(encounter),
        tags=("turning",),
    )


def __climbing_from_below__() -> Scenario:
    ownship = Flight("OWN")
    # Reaches our altitude exactly at the encounter (about 1300 fpm).
    climb_rate = CLIMB_FROM_BELOW_FEET * 60.0 / DEFAULT_ENCOUNTER_SECONDS

    return Scenario(
        "Climbing up from below",
        f"Starts {CLIMB_FROM_BELOW_FEET:.0f} ft below, climbing {climb_rate:.0f} fpm, converging from the right.",
        ownship,
        (Flight.meeting(
            ownship, "N9CL", DEFAULT_ENCOUNTER_SECONDS, -60.0, speed=110.0,
            legs=(Leg(vertical_speed=climb_rate),),
        ),),
        tags=("altitude",),
    )


def __overhead__() -> Scenario:
    encounter = 40.0
    ownship = Flight("OWN")

    return Scenario(
        "Crossing 1500 ft above",
        "Level, 1500 ft above us, crosses directly overhead.",
        ownship,
        (Flight.meeting(
            ownship, "N10OH", encounter, 90.0, speed=120.0,
            miss_feet=1500.0,
        ),),
        **__timing__(encounter),
        tags=("altitude", "no-threat"),
    )


def __on_ground_below__() -> Scenario:
    ownship = Flight("OWN", altitude=2500.0)

    return Scenario(
        "On the ground below us",
        "Taxiing at an airport 2000 ft below as we fly over it.",
        ownship,
        (Flight.meeting(
            ownship, "N11GR", DEFAULT_ENCOUNTER_SECONDS, 45.0, speed=15.0,
            miss_feet=-2000.0, on_ground=True,
        ),),
        tags=("altitude", "no-threat"),
    )


def __unknown_altitude__() -> Scenario:
    encounter = 40.0
    ownship = Flight("OWN")

    return Scenario(
        "No altitude reported",
        "Converging from the left; its transponder sends no altitude.",
        ownship,
        (Flight.meeting(
            ownship, "N12UK", encounter, 90.0, reports_altitude=False,
        ),),
        **__timing__(encounter),
        tags=("altitude",),
    )


def __pressure_offset__() -> Scenario:
    encounter = 28.0
    ownship = Flight("OWN")

    return Scenario(
        "High pressure day (30.42)",
        "Head-on at OUR altitude, but it reports pressure altitude 500 ft low.",
        ownship,
        (Flight.meeting(ownship, "N13PA", encounter, 180.0),),
        pressure_altitude_offset=-500.0,
        **__timing__(encounter),
        tags=("altitude",),
    )


def __busy_airport__() -> Scenario:
    encounter = 40.0
    # Seeded, so it is the same busy airport every time.
    chooser = random.Random(1234)
    ownship = Flight("OWN", altitude=2000.0, speed=95.0)
    traffic = [
        Flight.meeting(ownship, "N14TH", encounter, -100.0, speed=105.0),
    ]

    for index in range(24):
        is_on_ground = index % 6 == 0
        is_circling = not is_on_ground and index % 3 == 0
        legs = (Leg(turn_rate=chooser.choice([-3.0, 3.0])),) if is_circling else STRAIGHT_AND_LEVEL

        traffic.append(Flight.relative_to(
            ownship,
            f"N{100 + index}",
            clock=chooser.uniform(0.0, 360.0),
            range_nm=chooser.uniform(0.3, 4.0),
            altitude_offset=-1500.0 if is_on_ground else chooser.uniform(-1500.0, 1500.0),
            relative_track=chooser.uniform(0.0, 360.0),
            speed=chooser.uniform(5.0, 20.0) if is_on_ground else chooser.uniform(70.0, 140.0),
            legs=legs,
            on_ground=is_on_ground,
        ))

    return Scenario(
        "Busy airport",
        "24 aircraft nearby (some circling, some on the ground) and one threat.",
        ownship,
        tuple(traffic),
        **__timing__(encounter),
        tags=("clutter",),
    )


SCENARIOS = [
    __head_on__(),
    __converging_right__(),
    __overtaking__(),
    __being_overtaken__(),
    __parallel__(),
    __diverging__(),
    __pattern_turn_to_final__(),
    __ownship_turning__(),
    __climbing_from_below__(),
    __overhead__(),
    __on_ground_below__(),
    __unknown_altitude__(),
    __pressure_offset__(),
    __busy_airport__(),
]
