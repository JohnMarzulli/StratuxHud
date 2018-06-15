import pygame

from lib.display import RED
from lib.task_timer import TaskTimer


class AhrsNotAvailable(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('AhrsNotAvailable')
        self.__not_available_lines__ = []

        width, height = framebuffer_size

        self.__not_available_lines__.append([[0, 0], [width, height]])
        self.__not_available_lines__.append([[0, height], [width, 0]])
        self.__na_color__ = RED
        self.__na_line_width__ = 20

    def render(self, framebuffer, orientation):
        """
        Render an "X" over the screen to indicate the AHRS is not
        available.
        """

        self.task_timer.start()
        pygame.draw.line(framebuffer, self.__na_color__, self.__not_available_lines__[
                         0][0], self.__not_available_lines__[0][1], self.__na_line_width__)
        pygame.draw.line(framebuffer, self.__na_color__, self.__not_available_lines__[
                         1][0], self.__not_available_lines__[1][1], self.__na_line_width__)
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(AhrsNotAvailable)
