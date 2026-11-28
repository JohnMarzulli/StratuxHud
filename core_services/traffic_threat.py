"""
How much of a collision hazard each piece of traffic is.

    NONE      Not a factor
    WARNING   Worth watching
    ALERT     Find it now
    CRITICAL  Collision possible within seconds

Each level is a protected bubble around us: a radius, a height above
and below, and how far ahead to look. Traffic gets the highest level
whose bubble it is in now, or is predicted to enter within that
level's look-ahead (see LEVEL_RULES).

Paths are predicted two ways, and the worse result is used:

    straight  Both aircraft hold their current track, speed and
              vertical speed.
    turning   We follow the turn our bank angle gives us; they follow
              the turning path TrafficToHud predicts for them.

The turning check catches the encounters a straight line misses: a
pattern turn onto final in front of us, or us turning into someone.

Predictions get less certain the further the aircraft are predicted
to move, so each bubble grows by a fraction of the predicted movement
(the *_UNCERTAINTY settings). Traffic that isn't moving relative to
us is judged on the bubbles as they are.

Altitude removes traffic that is well above or below and not closing
vertically. Altitudes are compared as GPS altitude where possible;
when traffic only gives pressure altitude, the height of each bubble
is padded (UNCONFIRMED_DATUM_PADDING_FEET), since pressure altitude
can be hundreds of feet from GPS altitude. Traffic that sends no
altitude is judged on distance alone.

assess() is a pure function of one report and our own data.
ThreatTracker adds hysteresis on top (a level goes up at once, but
only comes down once it has stayed down for a few seconds) so markers
do not flicker; INSTANCE is the one the HUD uses.
"""

import math
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from numbers import Number
from typing import Optional

from common_utils import units
from common_utils.authoritative_time import get_system_time
from data_sources.ahrs_data import AhrsData
from data_sources.traffic import Traffic


class ThreatLevel(IntEnum):
    NONE = 0
    WARNING = 1
    ALERT = 2
    CRITICAL = 3


@dataclass(frozen=True)
class LevelRule:
    radius_sm: float  # Horizontal radius of the bubble
    height_feet: float  # Above and below us
    look_ahead_seconds: float  # How far ahead entering it counts


# Highest level first.
LEVEL_RULES = [
    (ThreatLevel.CRITICAL, LevelRule(radius_sm=0.15, height_feet=600.0, look_ahead_seconds=20.0)),
    (ThreatLevel.ALERT, LevelRule(radius_sm=0.25, height_feet=1000.0, look_ahead_seconds=40.0)),
    (ThreatLevel.WARNING, LevelRule(radius_sm=0.5, height_feet=1200.0, look_ahead_seconds=60.0)),
]

# How much a bubble grows, as a fraction of how far the traffic is
# predicted to move relative to us (sideways, and up or down).
HORIZONTAL_UNCERTAINTY = 0.15
VERTICAL_UNCERTAINTY = 0.25

# Added to every bubble's height when traffic gives only pressure
# altitude, which can't be compared exactly with our GPS altitude.
UNCONFIRMED_DATUM_PADDING_FEET = 300.0

# Vertical speeds under this are noise; treat them as level.
LEVEL_FLIGHT_FPM = 200.0
# Nobody climbs or descends further than this within the look-ahead.
MAX_ALTITUDE_CHANGE_FEET = 1500.0

# Below this bank angle (degrees) we are flying straight.
MIN_TURN_BANK_DEGREES = 5.0
# Slower than this, a turn rate from bank angle is meaningless.
MIN_TURN_SPEED_KNOTS = 30.0

# Traffic on the ground is ignored while we are this far above it.
GROUND_TRAFFIC_IGNORED_ABOVE_FEET = 1000.0

# How often along the predicted paths separation is checked.
SAMPLE_SECONDS = 1.0

# A level must stay lower for this long before the shown level drops.
LEVEL_HOLD_SECONDS = 5.0
# Tracked traffic not seen for this long is forgotten.
FORGET_AFTER_SECONDS = 60.0

NM_PER_SM = units.yards_to_sm / units.yards_to_nm
GRAVITY = 9.80665
METERS_PER_SECOND_PER_KNOT = 0.514444

# Why traffic got its level.
REASON_PROXIMITY = "proximity"  # Inside the bubble right now
REASON_STRAIGHT = "straight"  # Predicted to enter it, holding course
REASON_TURNING = "turning"  # Predicted to enter it, turning
REASON_ALTITUDE = "altitude"  # Would be a threat, but is above/below
REASON_GROUND = "on ground"
REASON_CLEAR = "clear"
REASON_NO_DATA = "no data"  # Missing our position or theirs


@dataclass(frozen=True)
class ThreatAssessment:
    level: ThreatLevel
    reason: str
    # The moment that set the level: how far ahead, how far apart,
    # and the height difference (None when it has no altitude).
    seconds: Optional[float] = None
    distance_sm: Optional[float] = None
    vertical_feet: Optional[float] = None


NO_THREAT = ThreatAssessment(ThreatLevel.NONE, REASON_CLEAR)


def __number__(value) -> Optional[float]:
    if isinstance(value, Number) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)

    return None


def __to_local__(origin, latitude: float, longitude: float) -> tuple:
    """
    (east, north) in nautical miles from origin. Flat earth; fine for
    the few miles that matter here.
    """
    north = (latitude - origin[0]) * 60.0
    east = (longitude - origin[1]) * 60.0 * math.cos(math.radians(origin[0]))

    return east, north


def __velocity__(track: float, speed_knots: float) -> tuple:
    """
    (east, north) in nautical miles per second.
    """
    radians = math.radians(track)
    per_second = speed_knots / 3600.0

    return per_second * math.sin(radians), per_second * math.cos(radians)


def __altitude_change__(vertical_speed: Optional[float], seconds: float) -> float:
    if vertical_speed is None or abs(vertical_speed) < LEVEL_FLIGHT_FPM:
        return 0.0

    change = vertical_speed / 60.0 * seconds

    return max(-MAX_ALTITUDE_CHANGE_FEET, min(MAX_ALTITUDE_CHANGE_FEET, change))


def get_turn_rate(ownship: AhrsData) -> float:
    """
    Our turn rate (degrees per second, positive right) from our bank
    angle: rate = g * tan(bank) / speed. 0 when flying straight.
    """
    roll = __number__(ownship.roll)
    speed = __number__(ownship.groundspeed)

    if roll is None or speed is None:
        return 0.0

    if abs(roll) < MIN_TURN_BANK_DEGREES or speed < MIN_TURN_SPEED_KNOTS:
        return 0.0

    velocity = speed * METERS_PER_SECOND_PER_KNOT

    return math.degrees(GRAVITY * math.tan(math.radians(roll)) / velocity)


class __OwnPath__:
    """
    Where we will be, relative to where we are now.
    """

    def __init__(self, track: float, speed: float, turn_rate: float):
        self.track = track
        self.speed = speed
        self.turn_rate = turn_rate

    def at(self, seconds: float, is_turning: bool) -> tuple:
        if not is_turning or self.turn_rate == 0.0:
            east, north = __velocity__(self.track, self.speed)

            return east * seconds, north * seconds

        nm_per_second = self.speed / 3600.0
        start = math.radians(self.track)
        rate = math.radians(self.turn_rate)
        radius = nm_per_second / rate
        end = start + rate * seconds

        return (
            radius * (math.cos(start) - math.cos(end)),
            radius * (math.sin(end) - math.sin(start)),
        )


class __TrafficPath__:
    """
    Where the traffic will be, relative to where we are now.
    """

    def __init__(self, east, north, track, speed, timed_points):
        self.east = east
        self.north = north
        self.velocity = __velocity__(track, speed) if track is not None else (0.0, 0.0)
        self.timed_points = timed_points

    def at(self, seconds: float, is_turning: bool) -> Optional[tuple]:
        if not is_turning or len(self.timed_points) < 2:
            return (
                self.east + self.velocity[0] * seconds,
                self.north + self.velocity[1] * seconds,
            )

        # Along TrafficToHud's predicted path; None past its end.
        for start, end in zip(self.timed_points, self.timed_points[1:]):
            if start[0] <= seconds <= end[0]:
                span = end[0] - start[0]
                proportion = 0.0 if span <= 0.0 else (seconds - start[0]) / span

                return (
                    start[1] + (end[1] - start[1]) * proportion,
                    start[2] + (end[2] - start[2]) * proportion,
                )

        return None


def __level_for__(
    seconds: float,
    distance_sm: float,
    vertical_feet,
    moved_sm: float = 0.0,
    moved_feet: float = 0.0,
    datum_padding: float = 0.0,
):
    """
    The highest level whose bubble this predicted moment is inside.
    moved_* is how far the traffic is predicted to have moved relative
    to us by then, which is how uncertain the prediction is.
    """
    for level, rule in LEVEL_RULES:
        if seconds > rule.look_ahead_seconds:
            continue

        if distance_sm > rule.radius_sm + HORIZONTAL_UNCERTAINTY * moved_sm:
            continue

        if vertical_feet is not None:
            height = rule.height_feet + VERTICAL_UNCERTAINTY * moved_feet + datum_padding

            if abs(vertical_feet) > height:
                continue

        return level

    return ThreatLevel.NONE


def assess(traffic: Traffic, ownship: AhrsData) -> ThreatAssessment:
    """
    How much of a threat this traffic is to us, right now.
    """
    if ownship is None:
        return ThreatAssessment(ThreatLevel.NONE, REASON_NO_DATA)

    origin = ownship.position
    latitude, longitude = __number__(traffic.latitude), __number__(traffic.longitude)

    if (
        not ownship.gps_online
        or origin is None
        or __number__(origin[0]) is None
        or __number__(origin[1]) is None
        or latitude is None
        or longitude is None
    ):
        return ThreatAssessment(ThreatLevel.NONE, REASON_NO_DATA)

    # -- Altitudes ----------------------------------------------------------
    own_altitude = __number__(ownship.alt)
    gnss_altitude = traffic.get_gnss_altitude()
    traffic_altitude = gnss_altitude if gnss_altitude is not None else traffic.altitude
    datum_padding = 0.0 if gnss_altitude is not None else UNCONFIRMED_DATUM_PADDING_FEET
    has_altitudes = own_altitude is not None and traffic_altitude is not None

    if traffic.is_on_ground() and (
        not has_altitudes
        or own_altitude - traffic_altitude > GROUND_TRAFFIC_IGNORED_ABOVE_FEET
    ):
        return ThreatAssessment(ThreatLevel.NONE, REASON_GROUND)

    own_vertical_speed = __number__(ownship.vertical_speed)
    traffic_vertical_speed = __number__(traffic.vertical_speed)

    def vertical_at(seconds: float):
        if not has_altitudes:
            return None

        return (
            traffic_altitude + __altitude_change__(traffic_vertical_speed, seconds)
        ) - (own_altitude + __altitude_change__(own_vertical_speed, seconds))

    # -- Paths -------------------------------------------------------------
    own_speed = __number__(ownship.groundspeed) or 0.0
    own_track = __number__(ownship.gps_heading) or 0.0
    own_path = __OwnPath__(own_track, own_speed, get_turn_rate(ownship))

    east, north = __to_local__(origin, latitude, longitude)
    timed_points = [
        (seconds,) + __to_local__(origin, point_latitude, point_longitude)
        for seconds, point_latitude, point_longitude in traffic.get_timed_prediction_points()
    ]
    traffic_path = __TrafficPath__(
        east, north, __number__(traffic.track), __number__(traffic.speed) or 0.0, timed_points
    )

    models = [(REASON_STRAIGHT, False)]

    if own_path.turn_rate != 0.0 or traffic.is_turning_prediction():
        models.append((REASON_TURNING, True))

    longest_look_ahead = max(rule.look_ahead_seconds for _, rule in LEVEL_RULES)
    sample_count = int(longest_look_ahead / SAMPLE_SECONDS)

    starting_vertical = vertical_at(0.0)
    best = NO_THREAT
    # The worst it would be with altitude ignored, to tell "filtered
    # by altitude" apart from "nowhere near".
    best_ignoring_altitude = ThreatLevel.NONE

    for reason, is_turning in models:
        for sample in range(sample_count + 1):
            seconds = sample * SAMPLE_SECONDS
            theirs = traffic_path.at(seconds, is_turning)

            if theirs is None:
                break

            ours = own_path.at(seconds, is_turning)
            distance_sm = math.hypot(theirs[0] - ours[0], theirs[1] - ours[1]) / NM_PER_SM
            moved_sm = math.hypot(
                (theirs[0] - east) - ours[0], (theirs[1] - north) - ours[1]
            ) / NM_PER_SM
            vertical = vertical_at(seconds)
            moved_feet = 0.0 if vertical is None else abs(vertical - starting_vertical)
            level = __level_for__(
                seconds, distance_sm, vertical, moved_sm, moved_feet, datum_padding
            )
            best_ignoring_altitude = max(
                best_ignoring_altitude,
                __level_for__(seconds, distance_sm, None, moved_sm),
            )

            if level > best.level:
                best = ThreatAssessment(
                    level,
                    REASON_PROXIMITY if sample == 0 else reason,
                    seconds,
                    distance_sm,
                    vertical,
                )

            if best.level == ThreatLevel.CRITICAL:
                return best

    if best.level == ThreatLevel.NONE and best_ignoring_altitude > ThreatLevel.NONE:
        return ThreatAssessment(ThreatLevel.NONE, REASON_ALTITUDE)

    return best


class ThreatTracker:
    """
    Assesses traffic and steadies the result: a level goes up at once,
    but the shown level only comes down after the assessed level has
    stayed below it for LEVEL_HOLD_SECONDS.
    """

    def __init__(self):
        self.__lock__ = threading.Lock()
        # icao address -> (shown assessment, last time it was earned, last seen)
        self.__tracked__ = {}

    def assess(self, traffic: Traffic, ownship: AhrsData, now: datetime = None) -> ThreatAssessment:
        now = now if now is not None else get_system_time()
        current = assess(traffic, ownship)
        key = str(traffic.icao_address)

        with self.__lock__:
            shown, earned, _ = self.__tracked__.get(key, (current, now, now))

            if current.level >= shown.level:
                shown, earned = current, now
            elif (now - earned).total_seconds() >= LEVEL_HOLD_SECONDS:
                shown, earned = current, now

            self.__tracked__[key] = (shown, earned, now)
            self.__forget_old__(now)

        return shown

    def clear(self):
        with self.__lock__:
            self.__tracked__ = {}

    def __forget_old__(self, now: datetime):
        stale = [
            key
            for key, (_, _, last_seen) in self.__tracked__.items()
            if (now - last_seen).total_seconds() > FORGET_AFTER_SECONDS
        ]

        for key in stale:
            del self.__tracked__[key]


INSTANCE = ThreatTracker()
