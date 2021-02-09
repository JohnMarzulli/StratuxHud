from typing import Union

NOT_AVAILABLE = '---'


class AhrsData(object):
    """
    Class to hold the AHRS data
    """

    def __is_compass_heading_valid__(
        self
    ) -> bool:
        return self.compass_heading is not None and self.compass_heading <= 360

    def get_onscreen_projection_heading(
        self
    ) -> Union[int, str]:
        if self.__is_compass_heading_valid__():
            return int(self.compass_heading)

        if self.gps_online:
            return int(self.gps_heading)

        return NOT_AVAILABLE

    def get_onscreen_projection_display_heading(
        self
    ) -> Union[int, str]:
        try:
            if self.__is_compass_heading_valid__():
                return int(self.compass_heading)
        except:
            pass

        return NOT_AVAILABLE

    def get_onscreen_gps_heading(
        self
    ) -> Union[int, str]:
        """
            Returns a safe display version of the GPS heading
        """
        return int(self.gps_heading) if self.gps_online else NOT_AVAILABLE

    def get_heading(
        self
    ) -> Union[int, str]:
        try:
            if (self.compass_heading is None
                    or self.compass_heading > 360
                    or self.compass_heading < 0
                    or self.compass_heading is '') and self.gps_online:
                return int(self.gps_heading)

            if self.__is_compass_heading_valid__():
                return int(self.compass_heading)
        except:
            return NOT_AVAILABLE

        return NOT_AVAILABLE

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
