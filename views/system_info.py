import pygame
import socket
import datetime

import struct

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer
import lib.local_debug as local_debug
import units
import configuration
from ahrs_element import AhrsElement
from traffic import AdsbTrafficClient

if not local_debug.is_debug():
    import fcntl


def get_ip_address(ifname="wlan0"):
    """
    Returns the local IP address of this unit.

    Keyword Arguments:
        ifname {str} -- The lan device name on the RasPi to get the IP from. (default: {"wlan0"})

    Returns:
        string -- The IP address as a string.
    """

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


def get_cpu_temp():
    """
    Gets the cpu temperature on RasPi (Celsius)

    Returns:
        string -- The CPU temp to display
    """

    try:
        raspberry_pi_temp = open('/sys/class/thermal/thermal_zone0/temp')
        temp = float(raspberry_pi_temp.read())
        temp = temp/1000

        return "{0}C".format(temp)
    except:
        return '---'


def get_websocket_uptime():
    """
    Returns how long the websocket has been up and connected.

    Returns:
        string -- Time string of how long the socket has been connected.
    """

    if AdsbTrafficClient.INSTANCE is not None and AdsbTrafficClient.INSTANCE.last_message_received_time is not None:
        connection_uptime = (datetime.datetime.now(
        ) - AdsbTrafficClient.INSTANCE.create_time).total_seconds()

        if connection_uptime < 60:
            return "{} seconds".format(int(connection_uptime))
        elif connection_uptime < 360:
            return "{0:.1f} minutes".format(connection_uptime / 60)
        elif connection_uptime < 216000:
            return "{0:.1f} hours".format(connection_uptime / 3600)
        else:
            return "{0:.1f} days".format(connection_uptime / 216000)
    else:
        return "DISCONNECTED"


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
            "IP         : {}".format(get_ip_address()),
            "CPU        : {}".format(get_cpu_temp()),
            "SOCKET     : {}".format(get_websocket_uptime()),
            "DECLINATION: {}".format(configuration.CONFIGURATION.get_declination()),
            "OWNSHIP    : {}".format(configuration.CONFIGURATION.ownship)
        ]

        render_y = self.__text_y_pos__

        for line in info_lines:
            texture = self.__font__.render(line, True, BLUE, BLACK)
            framebuffer.blit(texture, (0, render_y))

            render_y = render_y - (self.font_height * 1.2)

        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(SystemInfo, True)
