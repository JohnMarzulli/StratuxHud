import math
from datetime import datetime, timedelta, timezone

from common_utils import fast_math, geo_math, simulated_values

from data_sources import ahrs_data


class AhrsSimulation(object):
    """
    Class to simulate the AHRS data.
    """

    MAX_COURSE_OFFSET_DEGREES = 45.0
    MAX_BANK_DEGREES = 45.0

    def __get_maneuver__(
        self,
        seconds_since_start: float
    ) -> 'tuple[float, float]':
        """
        Returns the (heading offset, roll) for the looping S-turn maneuver.
        Negative values are to the left.
        """
        turn = self.__seconds_to_45_degrees__
        cycle_length = self.__on_course_seconds__ + (4.0 * turn)
        t = seconds_since_start % cycle_length

        # Each leg: (duration, starting offset, ending offset)
        legs = [
            (self.__on_course_seconds__, 0.0, 0.0),
            (turn, 0.0, -self.MAX_COURSE_OFFSET_DEGREES),
            (2.0 * turn, -self.MAX_COURSE_OFFSET_DEGREES,
             self.MAX_COURSE_OFFSET_DEGREES),
            (turn, self.MAX_COURSE_OFFSET_DEGREES, 0.0)
        ]

        for duration, start_offset, end_offset in legs:
            if duration <= 0.0 or t > duration:
                t -= duration
                continue

            proportion = t / duration
            delta = end_offset - start_offset
            # Cosine easing so the bank rolls in from level, peaks mid-turn, and rolls out level.
            offset = start_offset + \
                (delta * (1.0 - math.cos(math.pi * proportion)) / 2.0)
            roll = math.copysign(self.MAX_BANK_DEGREES, delta) * \
                math.sin(math.pi * proportion) if delta != 0.0 else 0.0

            return offset, roll

        return 0.0, 0.0

    def simulate(
        self
    ):
        """
        Ticks the simulated data.
        """
        seconds_since_start = (datetime.now(
            timezone.utc) - self.__starting_time__).total_seconds()
        hours_since_start = seconds_since_start / 60.0 / 60.0

        proportion_into_simulation = hours_since_start / self.__hours_to_destination__

        simulated_lat = fast_math.interpolatef(
            self.__starting_lat__, self.__ending_lat__, proportion_into_simulation)
        simulated_long = fast_math.interpolatef(
            self.__starting_long__, self.__ending_long__, proportion_into_simulation)

        self.ahrs_data.pitch = self.pitch_simulator.simulate()
        course_offset, self.ahrs_data.roll = self.__get_maneuver__(
            seconds_since_start)
        self.ahrs_data.airspeed = self.speed_simulator.simulate()
        self.ahrs_data.groundspeed = self.ahrs_data.airspeed
        self.ahrs_data.alt = self.alt_simulator.simulate()
        self.ahrs_data.slip_skid = self.skid_simulator.simulate()
        self.ahrs_data.position = [simulated_lat, simulated_long]
        target_course = geo_math.get_bearing(
            self.ahrs_data.position, [self.__ending_lat__, self.__ending_long__])
        self.ahrs_data.compass_heading = fast_math.wrap_degrees(
            target_course + course_offset)
        self.ahrs_data.gps_heading = self.ahrs_data.compass_heading

    def update(
        self
    ):
        """
        Updates the simulation and serves as the interface for the
        the AHRS/Simulation/Other sourcing
        """

        self.simulate()

    def get_ahrs(
        self
    ):
        """
        Returns the current simulated values for the AHRS data.

        Returns:
            AhrsData -- The current simulated values.
        """
        return self.ahrs_data

    def __init__(
        self,
        seconds_to_45_degrees: float = 15.0,
        on_course_seconds: float = 30.0
    ):
        self.ahrs_data = ahrs_data.AhrsData()
        self.__seconds_to_45_degrees__ = seconds_to_45_degrees
        self.__on_course_seconds__ = on_course_seconds

        # Simulate a flight from KAWO to OSH
        kawo = [48.16075, -122.15902777]
        kosh = [44.0, -88.5]
        # oregon = [45.0, -122.8]

        self.__starting_lat__ = kawo[0]
        self.__starting_long__ = kawo[1]

        self.__ending_lat__ = kosh[0]
        self.__ending_long__ = kosh[1]

        # In Oregon to help debug NEXRAD decoding
        # self.__starting_lat__ = 45.0
        # self.__starting_long__ = -122.8
        # self.__ending_lat__ = 45.2
        # self.__ending_long__ = -122.8

        self.ahrs_data.position = [
            self.__starting_lat__, self.__starting_long__]

        self.__hours_to_destination__ = 17.5
        self.__starting_time__ = datetime.now(timezone.utc)
        self.__end_time__ = self.__starting_time__ + timedelta(hours=17.5)

        self.pitch_simulator = simulated_values.SimulatedValue(1, 30, -1)
        self.speed_simulator = simulated_values.SimulatedValue(5, 10, 1, 0, 85)
        self.alt_simulator = simulated_values.SimulatedValue(
            10,
            100,
            -1,
            0,
            200)
        self.skid_simulator = simulated_values.SimulatedValue(
            0.5,
            1.5,
            1)
