import pygame

import display
from lib.task_timer import TaskTimer


class Altitude(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Altitude')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        altitude_text = str(int(orientation.alt)) + "' MSL"
        alt_texture = self.__font__.render(
            altitude_text, True, display.WHITE, display.BLACK)
        text_width, text_height = alt_texture.get_size()

        framebuffer.blit(
            alt_texture, (self.__rhs__ - text_width, self.__text_y_pos__))
        self.task_timer.stop()
