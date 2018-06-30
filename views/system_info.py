import pygame
import socket

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer
import units
from ahrs_element import AhrsElement


class SystemInfo(AhrsElement):
    def uses_ahrs(self):
        """
        The diagnostics page does not use AHRS.
        
        Returns:
            bool -- Always returns False.
        """

        return False

    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Time')
        self.__font__ = font
        self.font_height = font.get_height()
        text_half_height = int(self.font_height) >> 1
        self.__text_y_pos__ = framebuffer_size[1] -  text_half_height - self.font_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = int(framebuffer_size[0] * 0.01)
        self.__center_x__ = framebuffer_size[0] >> 1

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)

        ip_text = "IP: {}".format(host_ip)
        ip_texture = self.__font__.render(ip_text, True, BLUE, BLACK)

        framebuffer.blit(ip_texture, (0, self.__text_y_pos__))

        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(SystemInfo, True)
