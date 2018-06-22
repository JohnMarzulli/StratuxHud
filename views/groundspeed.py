import pygame

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer
import units


class Groundspeed(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Groundspeed')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = (text_half_height << 2) + \
            center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = int(framebuffer_size[0] * 0.01)

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        # TODO - Pass in the configuration to all elements so they can have access to the unit types.
        groundspeed_text = "{0:.1f}".format(orientation.g_load).rjust(5) + units.UNIT_LABELS[units.STATUTE][units.SPEED]
        texture = self.__font__.render(
            groundspeed_text, True, WHITE, BLACK)

        framebuffer.blit(
            texture, (self.__left_x__, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(Groundspeed, True)
