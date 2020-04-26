from numbers import Number

import pygame

from common_utils.task_timer import TaskTimer
from data_sources.ahrs_data import AhrsData
from rendering import colors, display
from views.ahrs_element import AhrsElement
from views.hud_elements import run_ahrs_hud_element


class Altitude(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('Altitude')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__rhs__ = int(framebuffer_size[0])  # was 0.9

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()
        is_altitude_valid = orientation.alt is not None and isinstance(
            orientation.alt,
            Number)
        altitude_text = str(int(orientation.alt)) + \
            "' MSL" if is_altitude_valid else AhrsElement.INOPERATIVE_TEXT
        color = colors.WHITE if is_altitude_valid else colors.RED
        alt_texture = self.__font__.render(
            altitude_text,
            True,
            color,
            colors.BLACK)
        text_width, text_height = alt_texture.get_size()

        framebuffer.blit(
            alt_texture,
            (self.__rhs__ - text_width, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    run_ahrs_hud_element(Altitude)
