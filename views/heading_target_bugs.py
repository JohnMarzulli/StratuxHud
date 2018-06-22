import pygame

from adsb_element import AdsbElement
from hud_elements import *

import testing
testing.load_imports()

from lib.task_timer import TaskTimer


class HeadingTargetBugs(AdsbElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, configuration):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, configuration)

        self.task_timer = TaskTimer('HeadingTargetBugs')
        self.__listing_text_start_y__ = int(self.__font__.get_height())
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
        heading_bugs = HudDataCache.HEADING_BUGS

        if heading_bugs is None or len(heading_bugs) == 0:
            framebuffer.blit(HudDataCache.get_cached_text_texture("NO TARGETS", self.__font__),
                             (self.__listing_text_start_x__, self.__listing_text_start_y__))

            self.task_timer.stop()
            return

        for bug in heading_bugs:
            # Render using the Above us bug
            # target_bug_scale = 0.04
            target_bug_scale = get_reticle_size(bug.distance)

            heading_bug_x = get_heading_bug_x(
                heading, bug.bearing, self.__pixels_per_degree_x__)

            additional_info_text = self.__get_additional_target_text__(
                bug, orientation)

            self.__render_heading_bug__(framebuffer,
                                        str(bug.get_identifer()),
                                        additional_info_text,
                                        heading_bug_x,
                                        target_bug_scale,
                                        False)
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(HeadingTargetBugs)
