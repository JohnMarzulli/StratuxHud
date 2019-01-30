import math
import pygame

from adsb_element import AdsbElement
from hud_elements import get_reticle_size, get_heading_bug_x, HudDataCache, max_altitude_delta, max_target_bugs

import testing
import lib.display as display
testing.load_imports()

from lib.task_timer import TaskTimer


class AdsbTargetBugsOnly(AdsbElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size)

        self.task_timer = TaskTimer('AdsbTargetBugs')
        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__top_border__ = 0
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

        # Render using the Above us bug
        # target_bug_scale = 0.04
        target_bug_scale = get_reticle_size(traffic_report.distance)

        heading_bug_x = get_heading_bug_x(
            heading, traffic_report.bearing, self.__pixels_per_degree_x__)

        try:
            is_below = (orientation.alt - 100) > traffic_report.altitude
            reticle, reticle_edge_positon_y = self.get_below_reticle(
                heading_bug_x, target_bug_scale) if is_below else self.get_above_reticle(heading_bug_x, target_bug_scale)

            bug_color = display.BLUE if traffic_report.is_on_ground() == True else display.RED

            pygame.draw.polygon(framebuffer, bug_color, reticle)
        except:
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

        reports_to_show = filter(lambda x: math.fabs(x.altitude - orientation.alt) < max_altitude_delta, traffic_reports)
        reports_to_show = reports_to_show[:max_target_bugs]

        [self.__render_traffic_heading_bug__(
            traffic_report, heading, orientation, framebuffer) for traffic_report in reports_to_show]

        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(AdsbTargetBugsOnly)
