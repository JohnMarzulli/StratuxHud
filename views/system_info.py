import commands
from traffic import AdsbTrafficClient
from ahrs_element import AhrsElement
import configuration
import units
import lib.local_debug as local_debug
import lib.colors as colors
from lib.task_timer import TaskTimer
from lib.display import *
import pygame
import socket
import datetime
import math

import struct

import testing
testing.load_imports()


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
            ip_addr = commands.getoutput('hostname -I').strip()
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
            return ("{} seconds".format(int(connection_uptime)), YELLOW)
        elif connection_uptime < 360:
            return ("{0:.1f} minutes".format(connection_uptime / 60), GREEN)
        elif connection_uptime < 216000:
            return ("{0:.1f} hours".format(connection_uptime / 3600), GREEN)
        else:
            return ("{0:.1f} days".format(connection_uptime / 216000), GREEN)
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
        self.__update_ip_timer__ = 0
        self.__update_temp_timer__ = 0
        self.__ip_address__ = get_ip_address()
        self.__cpu_temp__ = None
        self.__framebuffer_size__ = framebuffer_size

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        self.__update_ip_timer__ -= 1
        if self.__update_ip_timer__ <= 0:
            self.__ip_address__ = get_ip_address()
            self.__update_ip_timer__ = 120
        
        self.__update_temp_timer__ -= 1
        if self.__update_temp_timer__ <= 0:
            self.__cpu_temp__ = get_cpu_temp()
            self.__update_temp_timer__ = 60

        info_lines = [["VERSION     : ", [configuration.VERSION, YELLOW]]]


        addresses = self.__ip_address__[0].split(' ')
        for addr in addresses:
            info_lines.append(
                ["IP          : ", (addr, self.__ip_address__[1])])

        # Status lines are pushed in as a stack.
        # First line in the array is at the bottom.
        # Last line in the array is towards the top.
        info_lines.append(["HUD CPU     : ", self.__cpu_temp__])
        info_lines.append(["SOCKET      : ", get_websocket_uptime()])
        info_lines.append(["DECLINATION : ", [str(configuration.CONFIGURATION.get_declination()), BLUE]])
        info_lines.append(["OWNSHIP     : ", [configuration.CONFIGURATION.ownship, BLUE]])
        info_lines.append(["DISPLAY RES : ", ["{} x {}".format(self.__framebuffer_size__[0], self.__framebuffer_size__[1]), BLUE]])

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

            render_y = render_y - (self.font_height * 1.1)

        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    hud_elements.run_ahrs_hud_element(SystemInfo, True)
