"""
Handles determining how far out we care about traffic.
"""

from collections import deque
from datetime import datetime, timedelta

from common_utils import fast_math, geo_math, units
from data_sources.ahrs_data import AhrsData

DEFAULT_REPORT_PERIOD_SECONDS = 15


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
        report_period_seconds=DEFAULT_REPORT_PERIOD_SECONDS,
        max_reports=1000,
    ) -> None:
        super().__init__()

        self.__breadcrumbs__ = deque()
        self.speed = 0.0
        self.__max_reports__ = max_reports
        self.__speed_calculation_period_seconds__ = speed_calculation_period_seconds
        self.__report_period_seconds__ = report_period_seconds

    def __report__(
        self,
        position: list
    ):
        if position is None or position[0] is None or position[1] is None:
            return False

        if len(self.__breadcrumbs__) == 0:
            self.__breadcrumbs__.append(BreadcrumbReport(position))

            return True

        time_since_last_report = datetime.utcnow() - self.__breadcrumbs__[-1].timestamp

        if time_since_last_report.total_seconds() < self.__report_period_seconds__:
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

        # Find an average (mean) GPS position
        # Then find the median timestamp.
        #
        # Use the MEAN position with the last position....
        # the MEDIAN timestamp with the last timestamp.
        # Finally find the distance and average everything out.

        oldest_report_to_process = int(self.__speed_calculation_period_seconds__ / self.__report_period_seconds__)

        if self.__breadcrumbs__ is None or len(self.__breadcrumbs__) == 0:
            return 0.0

        current_size = len(self.__breadcrumbs__)

        if current_size < 3:
            return 0.0

        oldest_report_to_process = self.__breadcrumbs__[-min(current_size, oldest_report_to_process)]
        latest_report = self.__breadcrumbs__[-1]
        disance = geo_math.get_distance(oldest_report_to_process.position, latest_report.position)

        # This gives us Statue Miles per second
        delta_time = (latest_report.timestamp - oldest_report_to_process.timestamp).total_seconds()
        speed = disance / delta_time if delta_time > 0.0 else 0.0

        statute_miles_per_hour = speed * 3600

        # Distance is always in yards with the Stratux,
        # we will follow that pattern.
        return statute_miles_per_hour * units.yards_to_sm

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
