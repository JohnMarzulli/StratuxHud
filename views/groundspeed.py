import pygame

import testing
testing.load_imports()

import lib.display as display
from lib.task_timer import TaskTimer
import units
from ahrs_element import AhrsElement
import configuration


class Groundspeed(AhrsElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Groundspeed')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = (text_half_height << 2) + \
            center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = 0  # WAS int(framebuffer_size[0] * 0.01)

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        speed_units = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY, units.STATUTE)

        groundspeed_text = units.get_converted_units_string(
            speed_units, orientation.groundspeed * units.feet_to_nm, unit_type=units.SPEED, decimal_places=False)

        texture = self.__font__.render(
            groundspeed_text, True, display.WHITE, display.BLACK)

        framebuffer.blit(
            texture, (self.__left_x__, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(Groundspeed, True)
