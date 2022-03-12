"""
Handles determining how far out we care about traffic.
"""

import math
from collections import deque
from datetime import datetime, timedelta

from common_utils import fast_math, geo_math, units
from data_sources import ahrs_data
from data_sources.ahrs_data import AhrsData

MAXIMUM_POSITION_SAMPLE_RATE = 1
MINIMUM_POSITION_SAMPLE_RATE = 15
MAX_ROLL = 60.0
MAXIMUM_REPORTS_PER_MINUTE = int(60 / MAXIMUM_POSITION_SAMPLE_RATE)
MAXIMUM_REPORTS_PER_HOUR = int(MAXIMUM_REPORTS_PER_MINUTE * 60)

DEFAULT_MAX_REPORTS = MAXIMUM_REPORTS_PER_HOUR * 2


def get_position_sample_rate(
    roll_degrees: float
) -> float:
    """
    Given a roll rate, determine how often the position same needs to be taken.
    This allows us to record turns in better fidelity than flying straight.
    It also makes for a sparse-array style storage.

    Args:
        roll_degrees (float): The roll of the aircraft.

    Returns:
        float: How many seconds between position samples need to happen
    """

    absolute_roll = math.fabs(roll_degrees)
    # Make sure we only interpolate between 0 and 60 degrees
    clamped_roll = min(MAX_ROLL, absolute_roll)
    proportion = clamped_roll / MAX_ROLL
    exponential_proportion = math.sqrt(proportion)
    sample_rate = (1.0 - exponential_proportion) * (MINIMUM_POSITION_SAMPLE_RATE - MAXIMUM_POSITION_SAMPLE_RATE)
    sample_rate = MAXIMUM_POSITION_SAMPLE_RATE + sample_rate
    return sample_rate


class BreadcrumbReport:
    def __init__(
        self,
        position: list
    ) -> None:
        super().__init__()

        self.position = position
        self.timestamp = datetime.utcnow()


class Breadcrumbs:
    def __init__(
        self,
        speed_calculation_period_seconds=240,
        max_reports=DEFAULT_MAX_REPORTS,
    ) -> None:
        super().__init__()

        self.__breadcrumbs__ = deque()
        self.speed = ahrs_data.NOT_AVAILABLE
        self.__max_reports__ = int(max_reports)
        self.__speed_calculation_period_seconds__ = speed_calculation_period_seconds
        self.__seconds_of_trail_to_show__ = 60 * 60

    def __get_seconds_since_last_report_time__(
        self
    ) -> datetime:
        if (self.__breadcrumbs__ is not None) and (len(self.__breadcrumbs__) > 0):
            time_since_last_report = datetime.utcnow() - self.__breadcrumbs__[-1].timestamp

            return time_since_last_report.total_seconds()

        return MINIMUM_POSITION_SAMPLE_RATE * 2

    def __report__(
        self,
        position: list
    ):
        if position is None or position[0] is None or position[1] is None:
            return False

        self.__breadcrumbs__.append(BreadcrumbReport(position))

        return True

    def __get_speed_estimate__(
        self
    ) -> float:
        """
        Generates a guess at our REAL groundspeed based on where we have been.
        The idea is to take into account work in the pattern and keep our
        traffic zoom distance appropriate.

        In the pattern or low level work, you may be circling something causing
        you really to have a zero ground speed BUT your instantaneous speed is 100MPH

        Returns:
            float: [description]
        """

        if self.__breadcrumbs__ is None or len(self.__breadcrumbs__) == 0:
            return ahrs_data.NOT_AVAILABLE

        current_size = len(self.__breadcrumbs__)

        if current_size < 5:
            return ahrs_data.NOT_AVAILABLE

        oldest_timestamp_to_process = datetime.utcnow() - timedelta(seconds=self.__speed_calculation_period_seconds__)
        reports = list(filter(lambda x: x.timestamp >= oldest_timestamp_to_process, self.__breadcrumbs__))

        oldest_report_to_process = reports[0]
        latest_report = reports[-1]
        distance = geo_math.get_distance(oldest_report_to_process.position, latest_report.position)

        # This gives us Statue Miles per second
        delta_time = (latest_report.timestamp - oldest_report_to_process.timestamp).total_seconds()
        speed = distance / delta_time if delta_time > 0.0 else ahrs_data.NOT_AVAILABLE

        statute_miles_per_hour = speed * 3600

        # Distance is always in yards with the Stratux,
        # we will follow that pattern.
        return statute_miles_per_hour * units.yards_to_sm

    def get_trail(
        self
    ) -> list:
        """
        Get the list of positions ALONG with their relative age (proportion)
        compared to the report period.

        A proportion of 1.0 means the position report was just made.
        A proportion of 0.0 means the report is old and about to be ignored.

        Returns:
            list: A list of position and relative age.
        """

        if self.__breadcrumbs__ is None or len(self.__breadcrumbs__) == 0:
            return []

        current_size = len(self.__breadcrumbs__)

        if current_size < 2:
            return []

        now = datetime.utcnow()
        oldest_trail_report = now - timedelta(seconds=self.__seconds_of_trail_to_show__)
        reports = list(filter(lambda x: x.timestamp >= oldest_trail_report, self.__breadcrumbs__))

        return [[report.position, 1.0 - ((now - report.timestamp).total_seconds() / self.__seconds_of_trail_to_show__)]
                for report in reports]

    def update(
        self,
        orientation: AhrsData
    ) -> bool:
        """
        Request to update the breadcrumbs with our
        current position.        

        Args:
            orientation (AhrsData): Takes the AhrsData.Position (list)

        Returns:
            bool: True if the position report was added to the breadcrumbs
        """

        seconds_since_last_update = MINIMUM_POSITION_SAMPLE_RATE + MAXIMUM_POSITION_SAMPLE_RATE
        sample_rate = get_position_sample_rate(orientation.roll) if orientation is not None else MINIMUM_POSITION_SAMPLE_RATE
        seconds_since_last_update = self.__get_seconds_since_last_report_time__()

        if seconds_since_last_update < sample_rate:
            return False

        while len(self.__breadcrumbs__) > self.__max_reports__:
            self.__breadcrumbs__.get()

        if self.__report__(orientation.position):
            self.speed = self.__get_speed_estimate__()

            return True

        return False


INSTANCE = Breadcrumbs()

if __name__ == '__main__':
    from configuration import configuration

    speed_units = configuration.CONFIGURATION.__get_config_value__(
        configuration.Configuration.DISTANCE_UNITS_KEY,
        units.STATUTE)

    # Run a simulated flight from Seattle to Oshkosh at about 91MPH.
    # Print out the speed when a new report has been updated.

    starting_lat = 47.6
    starting_long = -122.3
    ending_lat = 44.0
    ending_long = -88.5

    hours_to_destination = 17.5
    starting_time = datetime.utcnow()
    end_time = starting_time + timedelta(hours=17.5)

    while datetime.utcnow() < end_time:
        hours_since_start = ((datetime.utcnow() - starting_time).total_seconds() / 60.0) / 60.0
        proportion_into_simulation = hours_since_start / hours_to_destination

        simulated_lat = fast_math.interpolatef(starting_lat, ending_lat, proportion_into_simulation)
        simulated_long = fast_math.interpolatef(starting_long, ending_long, proportion_into_simulation)

        simulated_ahrs = AhrsData()
        simulated_ahrs.position = [simulated_lat, simulated_long]

        if INSTANCE.update(simulated_ahrs):
            converted_speed = units.get_converted_units_string(
                speed_units,
                INSTANCE.speed,
                unit_type=units.SPEED,
                decimal_places=False)

            print("TRK SPEED:{}".format(converted_speed))
