import pygame
import socket

import struct

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer
import lib.local_debug as local_debug
import units
from ahrs_element import AhrsElement

if not local_debug.is_debug():
    import fcntl

def get_ip_address(ifname = "wlan0"):
    if not local_debug.is_debug():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15])
            )[20:24])
        except:
            pass

    host_name = socket.gethostname()
    return socket.gethostbyname(host_name)

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

        host_ip = get_ip_address()

        ip_text = "IP: {}".format(host_ip)
        ip_texture = self.__font__.render(ip_text, True, BLUE, BLACK)

        framebuffer.blit(ip_texture, (0, self.__text_y_pos__))

        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(SystemInfo, True)
