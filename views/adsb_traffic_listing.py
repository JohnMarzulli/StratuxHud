"""
View that shows the list of nearby traffic
"""

from core_services import zoom_tracker
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
        icao = report[4]

        # if self.__show_list__:
        traffic_report = "{0} {1} {2} {3}".format(
            identifier.ljust(max_string_lengths[0]),
            bearing.rjust(max_string_lengths[1]),
            distance_text.rjust(max_string_lengths[2]),
            altitude.rjust(max_string_lengths[3]))

        return (icao, traffic_report)

    def __get_padded_traffic_reports__(
        self,
        traffic_reports: list,
        orientation: AhrsData
    ):
        pre_padded_text, max_string_lengths = self.__get_pre_padded_text_reports__(
            traffic_reports,
            orientation)

        return [self.__get_listing__(
            report,
            max_string_lengths) for report in pre_padded_text]

    def __get_report_text__(
        self,
        traffic: Traffic,
        orientation: AhrsData
    ):
        identifier = str(traffic.get_display_name())
        altitude_delta = int(traffic.altitude / 100.0)
        distance_text = self.__get_distance_string__(traffic.distance, True) if orientation.gps_online else NOT_AVAILABLE
        delta_sign = ''
        if altitude_delta > 0:
            delta_sign = '+'
        altitude_text = "{0}{1}".format(delta_sign, altitude_delta)
        bearing_text = "{0:.0f}".format(apply_declination(traffic.bearing)) if orientation.gps_online else NOT_AVAILABLE

        return [identifier, bearing_text, distance_text, altitude_text, traffic.icao_address]

    def __get_pre_padded_text_reports__(
        self,
        traffic_reports: list,
        orientation: AhrsData
    ):
        # We do not want to show traffic on the ground.
        reports_to_show = list(
            filter(
                lambda x: not x.is_on_ground(),
                traffic_reports))

        reports_to_show = list(
            filter(
                lambda x: zoom_tracker.INSTANCE.is_in_inner_range(
                    x.distance
                )[0],
                traffic_reports))

        # The __max_reports__ value is set based on the screen size
        # and how much can fit on the screen
        reports_to_show = reports_to_show[:self.__max_reports__]

        pre_padded_text = [['IDENT', 'BEAR', 'DIST', 'ALT', None]] + \
            [self.__get_report_text__(traffic, orientation) for traffic in reports_to_show]
        # An ICAO code is the worst case display length,
        # but add a little buffer so the columns do
        # not shift around.
        # len(max(pre_padded_text, key = lambda x: len(str(x[4])))[0])
        max_identifier_length = 10
        # Since the bearing length should never be any more the 3 digits
        max_bearing_length = 4
        # len(max(pre_padded_text, key = lambda x: len(x[2]))[2]) + 1
        max_distance_length = 10
        # We really should never get anything more than 35k above, but same some room
        # len(max(pre_padded_text, key = lambda x: len(x[3]))[3])
        max_altitude_length = 5

        return pre_padded_text, (max_identifier_length, max_bearing_length, max_distance_length, max_altitude_length)

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
                colors.BLACK,
                colors.YELLOW)

            y_pos += self.__next_line_distance__


if __name__ == '__main__':
    from views.hud_elements import run_hud_element
    run_hud_element(AdsbTrafficListing)
