import pygame

from adsb_element import *
from hud_elements import *

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
        self.__listing_text_start_y__ = int(self.__font__.get_height() * 2)
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__max_reports__ = int(
            (self.__height__ - self.__listing_text_start_y__) / self.__next_line_distance__)
        self.__top_border__ = int(self.__height__ * 0.2)
        self.__bottom_border__ = self.__height__ - int(self.__height__ * 0.1)

    def __get_padded_traffic_reports__(self, traffic_reports):
        max_identifier_length = 0
        max_bearing_length = 0
        max_altitude_length = 0
        max_distance_length = 0
        pre_padded_text = []

        max_identifier_length, max_distance_length, max_altitude_length = self.__get_pre_padded_text_reports__(
            traffic_reports, max_identifier_length, max_bearing_length, max_altitude_length, max_distance_length, pre_padded_text)

        out_padded_reports = []

        for report in pre_padded_text:
            identifier = report[0]
            bearing = str(apply_declination(float(report[1])))
            distance_text = report[2]
            altitude = report[3]
            icao = report[4]

            # if self.__show_list__:
            traffic_report = "{0} {1} {2} {3}".format(
                identifier.ljust(max_identifier_length),
                bearing.rjust(3),
                distance_text.rjust(max_distance_length),
                altitude.rjust(max_altitude_length))
            out_padded_reports.append((icao, traffic_report))

        return out_padded_reports

    def __get_pre_padded_text_reports__(self, traffic_reports, max_identifier_length, max_bearing_length, max_altitude_length, max_distance_length, pre_padded_text):
        report_count = 0
        for traffic in traffic_reports:
            # Do not list traffic too far away
            if report_count > self.__max_reports__ or traffic.distance > imperial_occlude or traffic.is_on_ground():
                continue

            report_count += 1

            identifier = str(traffic.get_identifer())
            altitude_delta = int(traffic.altitude / 100.0)
            distance_text = self.__get_distance_string__(traffic.distance)
            delta_sign = ''
            if altitude_delta > 0:
                delta_sign = '+'
            altitude_text = "{0}{1}".format(delta_sign, altitude_delta)
            bearing_text = "{0:.0f}".format(traffic.bearing)

            identifier_length = len(identifier)
            bearing_length = len(bearing_text)
            altitude_length = len(altitude_text)
            distance_length = len(distance_text)

            if identifier_length > max_identifier_length:
                max_identifier_length = identifier_length

            if bearing_length > max_bearing_length:
                max_bearing_length = bearing_length

            if altitude_length > max_altitude_length:
                max_altitude_length = altitude_length

            if distance_length > max_distance_length:
                max_distance_length = distance_length

            pre_padded_text.append(
                [identifier, bearing_text, distance_text, altitude_text, traffic.icao_address])

        return max_identifier_length, max_distance_length, max_altitude_length

    def render(self, framebuffer, orientation):
        # Render a heading strip along the top

        self.task_timer.start()

        # Get the traffic, and bail out of we have none
        traffic_reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

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
            framebuffer.blit(HudDataCache.get_cached_text_texture("NO TRAFFIC", self.__font__),
                             (x_pos, y_pos))

        for identifier, traffic_report in padded_traffic_reports:
            traffic_text_texture = HudDataCache.get_cached_text_texture(
                traffic_report, self.__font__)

            framebuffer.blit(
                traffic_text_texture, (x_pos, y_pos))

            y_pos += self.__next_line_distance__
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(AdsbTrafficListing)
