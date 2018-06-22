import math

import pygame

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer


class RollIndicator(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('RollIndicator')
        self.__roll_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        half_texture_height = int(font.get_height()) >> 1
        self.__font__ = font
        self.__text_y_pos__ = self.__center__[1] - half_texture_height

        for reference_angle in range(-180, 181):
            text = font.render(
                "{0:3}".format(int(math.fabs(reference_angle))), True, WHITE, BLACK)
            size_x, size_y = text.get_size()
            self.__roll_elements__[reference_angle] = (
                text, (size_x >> 1, size_y >> 1))

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        roll = int(orientation.roll)
        pitch = int(orientation.pitch)
        pitch_direction = ''
        if pitch > 0:
            pitch_direction = '+'
        attitude_text = "{0}{1:3} | {2:3}".format(pitch_direction, pitch, roll)

        roll_texture = self.__font__.render(
            attitude_text, True, BLACK, WHITE)
        texture_size = roll_texture.get_size()
        text_half_width, text_half_height = texture_size
        text_half_width = int(text_half_width / 2)
        framebuffer.blit(
            roll_texture, (self.__center__[0] - text_half_width, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(RollIndicator, False)
