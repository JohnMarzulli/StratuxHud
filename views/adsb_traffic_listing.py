import pygame

from adsb_element import *
from hud_elements import *
import utils
import testing
testing.load_imports()

from lib.task_timer import TaskTimer


class AdsbTrafficListing(AdsbElement):
    def uses_ahrs(self):
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- False as this element does not use AHRS data.
        """

        return False

    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size)

        self.task_timer = TaskTimer('AdsbTargetBugs')
        self.__listing_text_start_y__ = int(self.__font__.get_height())
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height())
        self.__max_reports__ = int(
            (self.__height__ - self.__listing_text_start_y__) / self.__next_line_distance__) - 1
        self.__top_border__ = int(self.__height__ * 0.2)
        self.__bottom_border__ = self.__height__ - int(self.__height__ * 0.1)

    def __get_listing__(self, report, max_string_lengths):
        identifier = report[0]
        try:
            bearing = str(utils.apply_declination(float(report[1])))
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

    def __get_padded_traffic_reports__(self, traffic_reports):
        pre_padded_text, max_string_lengths = self.__get_pre_padded_text_reports__(traffic_reports)

        out_padded_reports = [self.__get_listing__(report,
                                                   max_string_lengths) for report in pre_padded_text]

        return out_padded_reports
    
    def __get_report_text__(self, traffic):
        identifier = str(traffic.get_identifer())
        altitude_delta = int(traffic.altitude / 100.0)
        distance_text = self.__get_distance_string__(traffic.distance)
        delta_sign = ''
        if altitude_delta > 0:
            delta_sign = '+'
        altitude_text = "{0}{1}".format(delta_sign, altitude_delta)
        bearing_text = "{0:.0f}".format(traffic.bearing)

        return [identifier, bearing_text, distance_text, altitude_text, traffic.icao_address]


    def __get_pre_padded_text_reports__(self, traffic_reports):
        # We do not want to show traffic on the ground.
        reports_to_show = filter(lambda x: not x.is_on_ground(), traffic_reports)

        # The __max_reports__ value is set based on the screen size
        # and how much can fit on the screen
        reports_to_show = reports_to_show[:self.__max_reports__]

        pre_padded_text = [['IDENT', 'BEAR', 'DIST', 'ALT', None]] + [self.__get_report_text__(traffic) for traffic in reports_to_show]
        # An ICAO code is the worst case display length,
        # but add a little buffer so the columns do
        # not shift around.
        max_identifier_length = 10 #len(max(pre_padded_text, key = lambda x: len(str(x[4])))[0])
        # Since the bearing length should never be any more the 3 digits
        max_bearing_length = 4
        max_distance_length =  8 # len(max(pre_padded_text, key = lambda x: len(x[2]))[2]) + 1
        # We really should never get anything more than 35k above, but same some room
        max_altitude_length =  5 #len(max(pre_padded_text, key = lambda x: len(x[3]))[3])

        return pre_padded_text, (max_identifier_length, max_bearing_length, max_distance_length, max_altitude_length)

    def render(self, framebuffer, orientation):
        # Render a heading strip along the top

        self.task_timer.start()

        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()

        if traffic_reports is None:
            self.task_timer.stop()
            return

        # Render a list of traffic that we have positions
        # for, along with the tail number

        y_pos = self.__listing_text_start_y__
        x_pos = self.__listing_text_start_x__

        padded_traffic_reports = self.__get_padded_traffic_reports__(
            traffic_reports)

        if len(padded_traffic_reports) == 0:
            framebuffer.blit(HudDataCache.get_cached_text_texture("NO TRAFFIC", self.__font__)[0],
                             (x_pos, y_pos))

        for identifier, traffic_report in padded_traffic_reports:
            traffic_text_texture = HudDataCache.get_cached_text_texture(traffic_report,
                                                                        self.__font__)[0]

            framebuffer.blit(traffic_text_texture, (x_pos, y_pos))

            y_pos += self.__next_line_distance__
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(AdsbTrafficListing)
