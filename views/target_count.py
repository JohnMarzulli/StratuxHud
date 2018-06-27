import pygame

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer
import units
from ahrs_element import AhrsElement
from hud_elements import *


class TargetCount(AhrsElement):
    def uses_ahrs(self):
        """
        Does this element use AHRS data to render?
               
        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('TargetCount')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = 0 # WAS int(framebuffer_size[0] * 0.01)

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        # Get the traffic, and bail out of we have none

        text = "NO TARGETS"

        try:
            heading_bugs = HudDataCache.get_heading_bugs()
            count = len(heading_bugs)

            if count > 0:
                text = "{0} TARGETS".format(count)
        except:
            text = "ERROR"

        texture = self.__font__.render(text, True, WHITE, BLACK)

        framebuffer.blit(
            texture, (self.__left_x__, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(TargetCount, True)
