"""
View that shows the list of nearby traffic
"""

from data_sources.ahrs_data import NOT_AVAILABLE, AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors, text_renderer

from views.adsb_element import AdsbElement, apply_declination


class AdsbTrafficListing(AdsbElement):
    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- False as this element does not use AHRS data.
        """

        return False

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size,
            reduced_visuals)

        self.__listing_text_start_y__ = int(self.__font__.get_height())
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height())
        self.__max_reports__ = int(
            (self.__height__ - self.__listing_text_start_y__) / self.__next_line_distance__) - 1

    def __get_listing__(
        self,
        report: list,
        max_string_lengths: list
    ):
        identifier = report[0]
        try:
            bearing = str(apply_declination(float(report[1])))
        except:
            bearing = str(report[1])
        distance_text = report[2]
        altitude = report[3]
        delta = report[4]
        icao = report[5]

        # if self.__show_list__:
        traffic_report = "{0} {1} {2} {3} {4}".format(
            identifier.ljust(max_string_lengths[0]),
            bearing.rjust(max_string_lengths[1]),
            distance_text.rjust(max_string_lengths[2]),
            altitude.rjust(max_string_lengths[3]),
            delta.rjust(max_string_lengths[4]))

        return (icao, traffic_report)

    def __get_padded_traffic_reports__(
        self,
        traffic_reports: list,
        orientation: AhrsData
    ):
        pre_padded_text, max_string_lengths = self.__get_pre_padded_text_reports__(
            traffic_reports,
            orientation)

        if pre_padded_text is None or max_string_lengths is None:
            return []

        return [self.__get_listing__(
            report,
            max_string_lengths) for report in pre_padded_text]

    def __get_report_text__(
        self,
        traffic: Traffic,
        orientation: AhrsData
    ):
        identifier = str(traffic.get_display_name())
        display_alt = int(traffic.altitude)
        distance_text = self.__get_distance_string__(traffic.distance, True) if orientation.gps_online else NOT_AVAILABLE
        altitude_text = "{0}".format(display_alt)
        bearing_text = "{0:.0f}".format(apply_declination(traffic.bearing)) if orientation.gps_online else NOT_AVAILABLE
        alt_delta = int(((display_alt - orientation.alt) / 100) + 0.5)
        alt_sign = "+" if alt_delta >= 0 else ""
        delta_text = "{0}{1}".format(alt_sign, alt_delta)

        return [identifier, bearing_text, distance_text, altitude_text, delta_text, traffic.icao_address]

    def __get_pre_padded_text_reports__(
        self,
        traffic_reports: list,
        orientation: AhrsData
    ):
        reports_to_show = HudDataCache.get_nearby_traffic()

        if reports_to_show is None:
            return None, None

        # We do not want to show traffic on the ground.
        reports_to_show = list(
            filter(
                lambda x: not x.is_on_ground(),
                traffic_reports))

        # The __max_reports__ value is set based on the screen size
        # and how much can fit on the screen
        reports_to_show = reports_to_show[:self.__max_reports__]

        pre_padded_text = [['IDENT', 'BRG', 'DIST', 'ALT', 'DLT', None]] + \
            [self.__get_report_text__(traffic, orientation) for traffic in reports_to_show]
        # An ICAO code is the worst case display length,
        # but add a little buffer so the columns do
        # not shift around.
        # len(max(pre_padded_text, key = lambda x: len(str(x[4])))[0])
        max_identifier_length = 8
        # Since the bearing length should never be any more the 3 digits
        max_bearing_length = 3
        # len(max(pre_padded_text, key = lambda x: len(x[2]))[2]) + 1
        max_distance_length = 8
        # We really should never get anything more than 35k above, but same some room
        # len(max(pre_padded_text, key = lambda x: len(x[3]))[3])
        max_altitude_length = 5
        max_delta_length = max_altitude_length - 2

        return pre_padded_text, (max_identifier_length, max_bearing_length, max_distance_length, max_altitude_length, max_delta_length)

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        # Render a heading strip along the top

        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()

        if traffic_reports is None:
            return

        # Render a list of traffic that we have positions
        # for, along with the tail number

        y_pos = self.__listing_text_start_y__
        x_pos = self.__listing_text_start_x__

        padded_traffic_reports = self.__get_padded_traffic_reports__(
            traffic_reports,
            orientation)

        for identifier, traffic_report in padded_traffic_reports:
            text_renderer.render_text(
                framebuffer,
                self.__font__,
                traffic_report,
                [x_pos, y_pos],
                colors.YELLOW,
                colors.BLACK)

            y_pos += self.__next_line_distance__


if __name__ == '__main__':
    from views.hud_elements import run_hud_element
    run_hud_element(AdsbTrafficListing)
