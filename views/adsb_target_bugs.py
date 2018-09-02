import pygame

from adsb_element import AdsbElement
from hud_elements import *

import testing
testing.load_imports()

from lib.task_timer import TaskTimer


class AdsbTargetBugs(AdsbElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size)

        self.task_timer = TaskTimer('AdsbTargetBugs')
        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__max_reports__ = int(
            (self.__height__ - self.__listing_text_start_y__) / self.__next_line_distance__)
        self.__top_border__ = int(self.__height__ * 0.2)
        self.__bottom_border__ = self.__height__ - int(self.__height__ * 0.1)

    def render(self, framebuffer, orientation):
        # Render a heading strip along the top

        self.task_timer.start()
        heading = orientation.get_onscreen_projection_heading()

        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()

        if traffic_reports is None:
            self.task_timer.stop()
            return

        # Draw the heading bugs in reverse order so the traffic closest to
        # us will be the most visible
        traffic_bug_reports = sorted(
            traffic_reports, key=lambda traffic: traffic.distance, reverse=True)

        for traffic_report in traffic_bug_reports:
            if traffic_report.distance > imperial_occlude:
                continue

            try:
                altitude_delta = int(
                    (traffic_report.altitude - orientation.alt) / 100.0)

                # TEST - Ignore stuff crazy separated
                if math.fabs(altitude_delta) > 50:
                    continue
            finally:
                pass

            # Now find where to draw the reticle....
            reticle_x, reticle_y = self.__get_traffic_projection__(
                orientation, traffic_report)

            # Render using the Above us bug
            # target_bug_scale = 0.04
            target_bug_scale = get_reticle_size(traffic_report.distance)

            heading_bug_x = get_heading_bug_x(
                heading, traffic_report.bearing, self.__pixels_per_degree_x__)

            additional_info_text = self.__get_additional_target_text__(
                traffic_report, orientation)

            try:
                self.__render_heading_bug__(framebuffer,
                                            str(traffic_report.get_identifer()),
                                            additional_info_text,
                                            heading_bug_x,
                                            target_bug_scale,
                                            traffic_report.is_on_ground(),
                                            traffic_report.get_age())
            except Exception as e:
                print(str(e))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(AdsbTargetBugs)
