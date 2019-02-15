import math
import pygame

from .adsb_element import AdsbElement
from hud_elements import get_reticle_size, get_heading_bug_x, HudDataCache, imperial_occlude, max_altitude_delta, max_target_bugs

from . import testing
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
        self.__top_border__ = int(self.__height__ * 0.2)
        self.__bottom_border__ = self.__height__ - int(self.__height__ * 0.1)

    def __render_traffic_heading_bug__(self, traffic_report, heading, orientation, framebuffer):
        """
        Render a single heading bug to the framebuffer.

        Arguments:
            traffic_report {Traffic} -- The traffic we want to render a bug for.
            heading {int} -- Our current heading.
            orientation {Orientation} -- Our plane's current orientation.
            framebuffer {Framebuffer} -- What we are going to draw to.
        """

        heading_bug_x = get_heading_bug_x(
            heading, traffic_report.bearing, self.__pixels_per_degree_x__)

        additional_info_text = self.__get_additional_target_text__(
            traffic_report, orientation)

        try:
            self.__render_info_card__(framebuffer,
                                      str(traffic_report.get_identifer()),
                                      additional_info_text,
                                      heading_bug_x,
                                      traffic_report.get_age())
        except Exception as ex:
            print(f"EX:{ex}")
            pass

    def render(self, framebuffer, orientation):
        # Render a heading strip along the top

        self.task_timer.start()
        heading = orientation.get_onscreen_projection_heading()

        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()

        if traffic_reports is None:
            self.task_timer.stop()
            return

        traffic_reports = [x for x in traffic_reports if math.fabs(x.altitude - orientation.alt) < max_altitude_delta]
        traffic_reports = traffic_reports[:max_target_bugs]

        # Draw the heading bugs in reverse order so the traffic closest to
        # us will be the most visible
        traffic_reports.reverse()

        [self.__render_traffic_heading_bug__(
            traffic_report, heading, orientation, framebuffer) for traffic_report in traffic_reports]

        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(AdsbTargetBugs)
