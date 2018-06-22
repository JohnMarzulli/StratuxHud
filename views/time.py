import pygame

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer
import units


class Time(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Time')
        self.__font__ = font
        font_height = font.get_height()
        text_half_height = int(font_height) >> 1
        self.__text_y_pos__ = framebuffer_size[1] -  text_half_height - font_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = int(framebuffer_size[0] * 0.01)

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        time_text = str(orientation.utc_time) + "UTC"
        texture = self.__font__.render(time_text, True, YELLOW, BLACK)

        framebuffer.blit(texture, (self.__left_x__, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(Time, True)
