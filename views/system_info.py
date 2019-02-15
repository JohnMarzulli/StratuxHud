import pygame
import socket
import datetime
import math

import struct

from . import testing
testing.load_imports()

# pylint: disable=unused-wildcard-import
from lib.display import *
from lib.task_timer import TaskTimer
import lib.colors as colors
import lib.local_debug as local_debug
import units
import configuration
from .ahrs_element import AhrsElement
from traffic import AdsbTrafficClient

import subprocess

NORMAL_TEMP = 50
REDLINE_TEMP = 80


def get_ip_address():
    """
    Returns the local IP address of this unit.

    Returns:
        tuple -- The IP address as a string and the color to render it in.
    """

    try:
        if not local_debug.is_debug():
            ip_addr = subprocess.getoutput('hostname -I').strip()
            return (ip_addr, GREEN)
        else:
            host_name = socket.gethostname()
            return (socket.gethostbyname(host_name), GREEN)
    except:
        return ('UNKNOWN', RED)


def get_cpu_temp_text_color(temperature):
    color = GREEN

    if temperature > REDLINE_TEMP:
        color = RED
    elif temperature > NORMAL_TEMP:
        delta = float(temperature - NORMAL_TEMP)
        temp_range = float(REDLINE_TEMP - NORMAL_TEMP)
        delta = colors.clamp(0.0, delta, temp_range)
        proportion = delta / temp_range
        color = colors.get_color_mix(GREEN, RED, proportion)

    return color


def get_cpu_temp():
    """
    Gets the cpu temperature on RasPi (Celsius)

    Returns:
        string -- The CPU temp to display
    """

    color = GREEN

    try:
        # if not local_debug.is_debug():
        raspberry_pi_temp = open('/sys/class/thermal/thermal_zone0/temp')
        temp = float(raspberry_pi_temp.read())
        temp = temp/1000
        # else:
        #    temp = float(datetime.datetime.utcnow().second) + 30.0

        color = get_cpu_temp_text_color(temp)

        return ("{0}C".format(int(math.floor(temp))), color)
    except:
        return ('---', GRAY)


def get_websocket_uptime():
    """
    Returns how long the websocket has been up and connected.

    Returns:
        string -- Time string of how long the socket has been connected.
    """

    if AdsbTrafficClient.INSTANCE is not None:
        connection_uptime = (datetime.datetime.utcnow()
                             - AdsbTrafficClient.INSTANCE.create_time).total_seconds()

        if connection_uptime < 60:
            return (f"{int(connection_uptime)} seconds", YELLOW)
        elif connection_uptime < 360:
            return (f"{connection_uptime / 60:.1f} minutes", GREEN)
        elif connection_uptime < 216000:
            return (f"{connection_uptime / 3600:.1f} hours", GREEN)
        else:
            return (f"{connection_uptime / 216000:.1f} days", GREEN)
    else:
        return ("DISCONNECTED", RED)


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
        self.__text_y_pos__ = framebuffer_size[1] - \
            text_half_height - self.font_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = int(framebuffer_size[0] * 0.01)
        self.__center_x__ = framebuffer_size[0] >> 1

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        # Status lines are pushed in as a stack.
        # First line in the array is at the bottom.
        # Last line in the array is towards the top.
        info_lines = [
            ["VERSION     : ", [configuration.VERSION, YELLOW]],
            ["IP          : ", get_ip_address()],
            ["HUD CPU     : ", get_cpu_temp()],
            ["SOCKET      : ", get_websocket_uptime()],
            ["DECLINATION : ", [
                str(configuration.CONFIGURATION.get_declination()), BLUE]],
            ["OWNSHIP     : ", [configuration.CONFIGURATION.ownship, BLUE]]
        ]

        render_y = self.__text_y_pos__

        for line in info_lines:
            # Draw the label in a standard color.
            texture_lhs = self.__font__.render(line[0], True, BLUE, BLACK)
            framebuffer.blit(texture_lhs, (0, render_y))
            size = texture_lhs.get_size()

            # Draw the value in the encoded colors.
            texture_rhs = self.__font__.render(
                line[1][0], True, line[1][1], BLACK)
            framebuffer.blit(texture_rhs, (size[0], render_y))

            render_y = render_y - (self.font_height * 1.2)

        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    hud_elements.run_ahrs_hud_element(SystemInfo, True)
