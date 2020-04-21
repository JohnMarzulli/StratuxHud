from ahrs_element import AhrsElement
from lib.task_timer import TaskTimer
from numbers import Number
import lib.display as display
import pygame

import testing
testing.load_imports()


class Altitude(AhrsElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Altitude')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__rhs__ = int(framebuffer_size[0])  # was 0.9

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        is_altitude_valid = orientation.alt is not None and isinstance(orientation.alt, Number)
        altitude_text = str(int(orientation.alt)) + \
            "' MSL" if is_altitude_valid else AhrsElement.INOPERATIVE_TEXT
        color = display.WHITE if is_altitude_valid else display.RED
        alt_texture = self.__font__.render(
            altitude_text,
            True,
            color,
            display.BLACK)
        text_width, text_height = alt_texture.get_size()

        framebuffer.blit(
            alt_texture, (self.__rhs__ - text_width, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(Altitude)
