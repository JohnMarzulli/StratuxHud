"""
Data store to standardize AHRS data.
"""

from typing import Union

NOT_AVAILABLE = '---'


class AhrsData:
    """
    Class to hold the AHRS data
    """

    def __is_compass_heading_valid__(
        self
    ) -> bool:
        return self.compass_heading is not None \
            and self.compass_heading != '' \
            and self.compass_heading >= 0 \
            and self.compass_heading <= 360

    def get_onscreen_projection_heading(
        self
    ) -> Union[int, str]:
        """
        Get the value to display for our heading.
        Uses a fall-back system so at least one
        source of data is used.

        Attempts to use the compass first, falls back
        to the GPS track.

        Returns:
            Union[int, str]: The heading to display.
        """
        if self.__is_compass_heading_valid__():
            return int(self.compass_heading)

        if self.gps_online:
            return int(self.gps_heading)

        return NOT_AVAILABLE

    def get_onscreen_compass_heading(
        self
    ) -> Union[int, str]:
        """
        Get the heading from the compass, if available.

        Returns:
            Union[int, str]: The compass heading to display.
        """
        return int(self.compass_heading) if self.__is_compass_heading_valid__() else NOT_AVAILABLE

    def get_onscreen_gps_heading(
        self
    ) -> Union[int, str]:
        """
        Returns a safe display version of the GPS heading

        Returns:
            Union[int, str]: The gps track to display.
        """
        return int(self.gps_heading) if self.gps_online else NOT_AVAILABLE

    def get_compass_heading(
        self
    ) -> Union[int, str]:
        """
        Get the heading from the compass IF available.

        Returns:
            Union[int, str]: The compass heading, or indication it is not available.
        """
        return self.compass_heading if self.__is_compass_heading_valid__() else NOT_AVAILABLE

    def __init__(
        self
    ):
        self.roll = 0.0
        self.pitch = 0.0
        self.compass_heading = 0.0
        self.gps_heading = 0.0
        self.compass_heading = 0.0
        self.alt = 0.0
        self.position = (0, 0)  # lat, lon
        self.groundspeed = 0
        self.airspeed = 0
        self.vertical_speed = 0
        self.g_load = 1.0
        self.min_g = 1.0
        self.max_g = 1.0
        self.utc_time = None
        self.gps_online = True
        self.is_avionics_source = False
        self.slip_skid = None
