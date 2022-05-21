"""
Class to handle fetching orientation, and then
integrating (with priorty) multiple orientation
or AHRS sources into a single point.
"""

from common_utils import logging_object, tasks
from common_utils.logger import HudLogger
from configuration import configuration

from data_sources import ahrs_data, gdl90_ahrs_source


class Aircraft(logging_object.LoggingObject):
    """
    Class to handle fetching orientation, and then
    integrating (with priorty) multiple orientation
    or AHRS sources into a single point.
    """

    def update_orientation_in_background(
        self
    ):
        """
        Non-terminating loop for updating the AHRS.
        Inteded to be run from a thread.
        """

        print("starting")

        # pylint:disable=try-except-raise
        # pylint:disable=broad-except
        while True:
            try:
                self.__update_orientation__()
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                self.warn(f"update_orientation_in_background ex={ex}")

    def __init__(
        self,
        logger: HudLogger = None
    ):
        super().__init__(logger)

        self.ahrs_source = gdl90_ahrs_source.AhrsStratux(logger)

        tasks.RecurringTask(
            'UpdateStratuxAhrs',
            1.0 / configuration.TARGET_AHRS_FRAMERATE,
            self.__update_orientation__)

        tasks.RecurringTask(
            'UpdateAvionics',
            1.0 / configuration.TARGET_AHRS_FRAMERATE,
            self.__update_avionics_orientation__)

    def is_ahrs_available(
        self
    ) -> bool:
        """
        Returns True if the AHRS data is available
        """

        return self.ahrs_source is not None and self.ahrs_source.is_data_source_available()

    def get_orientation(
        self
    ) -> ahrs_data.AhrsData:
        """
        Get the current AHRS data for the aircraft.

        Returns:
            ahrs_data.AhrsData: The current AHRS data for the aircraft.
        """
        return self.ahrs_source.get_ahrs()

    def __update_orientation__(
        self
    ):
        if self.ahrs_source is not None:
            self.ahrs_source.update()

    def __update_avionics_orientation__(
        self
    ):
        if self.ahrs_source is not None:
            self.ahrs_source.update_avionics()


if __name__ == '__main__':
    import time
    plane = Aircraft()

    while True:
        print(plane.get_orientation().roll)
        time.sleep(1.0 / 60.0)
