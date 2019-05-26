import commands
from traffic import AdsbTrafficClient
from ahrs_element import AhrsElement
import aithre
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
        if local_debug.IS_LINUX and local_debug.IS_PI:
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
        if local_debug.IS_LINUX:
            linux_cpu_temp = open('/sys/class/thermal/thermal_zone0/temp')
            temp = float(linux_cpu_temp.read())
            temp = temp/1000

            color = get_cpu_temp_text_color(temp)

            return ("{0}C".format(int(math.floor(temp))), color)
    except:
        return ('---', GRAY)

    return ('---', GRAY)


def get_aithre_co_color(co_ppm):
    """
    Returns the color code for the carbon monoxide levels

    Arguments:
        co_ppm {int} -- Integer containing the Parts Per Million of CO

    Returns:
        color -- The color to display
    """
    color = BLUE

    if co_ppm > aithre.CO_WARNING:
        color = RED
    elif co_ppm > aithre.CO_SAFE:
        color = YELLOW

    return color


def get_aithre_battery_color(battery_percent):
    """
    Returns the color code for the Aithre battery level.

    Arguments:
        battery_percent {int} -- The percentage of battery.

    Returns:
        color -- The color to show the battery percentage in.
    """
    color = RED

    if battery_percent >= aithre.BATTERY_SAFE:
        color = GREEN
    elif battery_percent >= aithre.BATTERY_WARNING:
        color = YELLOW

    return color


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
        self.__line_spacing__ = 1.01

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

        info_lines = [["VERSION     : ", [configuration.VERSION, YELLOW]],
                      ["DECLINATION : ", [str(configuration.CONFIGURATION.get_declination()), BLUE]]]

        addresses = self.__ip_address__[0].split(' ')
        for addr in addresses:
            info_lines.append(
                ["IP          : ", (addr, self.__ip_address__[1])])

        if aithre.sensor is not None and configuration.CONFIGURATION.aithre_enabled:
            battery_stats = ["DISCONNECTED", RED]

            try:
                battery = aithre.sensor.get_battery()
                battery_suffix = "%"
                if isinstance(battery, basestring):
                    battery_suffix = ""
                if battery is not None:
                    battery_stats = ["{}{}".format(
                        battery, battery_suffix), get_aithre_battery_color(battery)]
            except Exception as ex:
                battery_stats = ["{}".format(ex), RED]

            info_lines.append(["AITHRE BAT  : ", battery_stats])

            co_stats = ["DISCONNECTED", RED]
            try:
                co_ppm = aithre.sensor.get_co_level()

                if co_ppm is not None:
                    co_stats = ["{} ppm".format(
                        co_ppm), get_aithre_co_color(co_ppm)]
            except Exception as ex:
                co_stats = ["{}".format(ex), RED]

            info_lines.append(["AITHRE CO   : ", co_stats])

        # Status lines are pushed in as a stack.
        # First line in the array is at the bottom.
        # Last line in the array is towards the top.
        info_lines.append(["HUD CPU     : ", self.__cpu_temp__])
        info_lines.append(["SOCKET      : ", get_websocket_uptime()])
        info_lines.append(
            ["OWNSHIP     : ", [configuration.CONFIGURATION.ownship, BLUE]])
        info_lines.append(["DISPLAY RES : ", ["{} x {}".format(
            self.__framebuffer_size__[0], self.__framebuffer_size__[1]), BLUE]])

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

            render_y = render_y - (self.font_height * self.__line_spacing__)

        self.task_timer.stop()


class Aithre(AhrsElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Aithre')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__lhs__ = 0
        self.__has_been_connected__ = False


    def render(self, framebuffer, orientation):
        self.task_timer.start()

        if aithre.sensor is not None and configuration.CONFIGURATION.aithre_enabled:
            co_level = aithre.sensor.get_co_level()

            if co_level is None or isinstance(co_level, basestring):
                if self.__has_been_connected__:
                    co_color = RED
                    co_ppm_text = "OFFLINE"
                else:
                    self.task_timer.stop()
                    return
            else:
                co_color = get_aithre_co_color(co_level)
                co_ppm_text = str(int(co_level)) + " PPM"
                self.__has_been_connected__ = True

            co_ppm_texture = self.__font__.render(
                co_ppm_text, True, co_color, BLACK)

            framebuffer.blit(
                co_ppm_texture, (self.__lhs__, self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(Aithre)

if __name__ == '__main__':
    import hud_elements

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    hud_elements.run_ahrs_hud_element(SystemInfo, True)
