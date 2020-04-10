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
from aithre import AithreClient

import struct

import testing
testing.load_imports()


NORMAL_TEMP = 50
REDLINE_TEMP = 80

CO_SAFE = 10
CO_WARNING = 49

BATTERY_SAFE = 75
BATTERY_WARNING = 25


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


def get_illyrian_spo2_color(spo2_level):
    """
    Gets the color for the SPO2 level
    """

    if spo2_level is None:
        return RED

    color = GREEN

    if spo2_level < 94:
        color = YELLOW

    if spo2_level < 90:
        color = RED

    return color


def get_aithre_co_color(co_ppm):
    """
    Returns the color code for the carbon monoxide levels

    Arguments:
        co_ppm {int} -- Integer containing the Parts Per Million of CO

    Returns:
        color -- The color to display
    """
    color = BLUE

    if co_ppm > CO_WARNING:
        color = RED
    elif co_ppm > CO_SAFE:
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

    if battery_percent >= BATTERY_SAFE:
        color = GREEN
    elif battery_percent >= BATTERY_WARNING:
        color = YELLOW

    return color


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
        self.__text_y_pos__ = framebuffer_size[1] - self.font_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = int(framebuffer_size[0] * 0.01)
        self.__center_x__ = framebuffer_size[0] >> 1
        self.__update_ip_timer__ = 0
        self.__update_temp_timer__ = 0
        self.__ip_address__ = get_ip_address()
        self.__cpu_temp__ = None
        self.__framebuffer_size__ = framebuffer_size
        self.__line_spacing__ = 1.01

    def __get_aithre_text_and_color__(self):
        """
        Gets the text and text color for the Aithre status.
        """

        if AithreClient.INSTANCE is None:
            return ('DISCONNECTED', RED) if configuration.CONFIGURATION.aithre_enabled else ('DISABLED', BLUE)

        co_report = AithreClient.INSTANCE.get_co_report()

        battery_text = 'UNK'
        battery_color = RED

        try:
            battery = co_report.battery
            battery_suffix = "%"
            if isinstance(battery, basestring):
                battery_suffix = ""
            if battery is not None:
                battery_color = get_aithre_battery_color(battery)
                battery_text = "bat:{}{}".format(battery, battery_suffix)
        except Exception as ex:
            battery_text = 'ERR'

        co_text = 'UNK'
        co_color = RED

        try:
            co_ppm = co_report.co

            if co_ppm is not None:
                co_text = 'co:{}ppm'.format(co_ppm)
                co_color = get_aithre_co_color(co_ppm)
        except Exception as ex:
            co_text = 'ERR'

        color = RED if co_color is RED or battery_color is RED else \
            (YELLOW if co_color is YELLOW or battery_color is YELLOW else BLUE)

        return ('{} {}'.format(co_text, battery_text), color)

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
                      ["DECLINATION : ", [
                          str(configuration.CONFIGURATION.get_declination()), BLUE]],
                      ["TRAFFIC     : ", [configuration.CONFIGURATION.get_traffic_manager_address(), BLUE]]]

        addresses = self.__ip_address__[0].split(' ')
        for addr in addresses:
            info_lines.append(
                ["IP          : ", (addr, self.__ip_address__[1])])

        info_lines.append(
            ["AITHRE      : ", self.__get_aithre_text_and_color__()])

        # Status lines are pushed in as a stack.
        # First line in the array is at the bottom.
        # Last line in the array is towards the top.
        info_lines.append(["HUD CPU     : ", self.__cpu_temp__])
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
    def uses_ahrs(self):
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Aithre')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y + (10 * text_half_height)
        self.__lhs__ = 0

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        if AithreClient.INSTANCE is not None and configuration.CONFIGURATION.aithre_enabled:
            co_level = AithreClient.INSTANCE.get_co_report()

            if (co_level.co is None and co_level.has_been_connected) or isinstance(co_level, basestring):
                co_color = RED
                co_ppm_text = "OFFLINE"
            elif not co_level.has_been_connected:
                self.task_timer.stop()
                return
            else:
                co_color = get_aithre_co_color(co_level.co)
                units_text = "PPM" if co_level.is_connected else ""
                co_ppm_text = "{}{}".format(co_level.co, units_text)

            co_ppm_texture = self.__font__.render(
                co_ppm_text, True, co_color, BLACK)

            framebuffer.blit(
                co_ppm_texture, (self.__lhs__, self.__text_y_pos__))
        self.task_timer.stop()


class Illyrian(AhrsElement):
    """
    Screen element to support the Illyrian blood/pulse oxymeter from Aithre
    """

    def uses_ahrs(self):
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Illyrian')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y + (6 * text_half_height)
        self.__pulse_y_pos__ = center_y + (8 * text_half_height)
        self.__lhs__ = 0
        self.__has_been_connected__ = False

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        if AithreClient.INSTANCE is not None and configuration.CONFIGURATION.aithre_enabled:
            report = AithreClient.INSTANCE.get_spo2_report()
            spo2_level = report.spo2
            heartbeat = report.heartrate
            heartbeat_text = "{}BPM".format(heartbeat)

            if spo2_level is None or isinstance(spo2_level, basestring):
                if self.__has_been_connected__:
                    spo2_color = RED
                    spo2_text = "OFFLINE"
                else:
                    self.task_timer.stop()
                    return
            else:
                spo2_color = get_illyrian_spo2_color(spo2_level)
                spo2_text = str(int(spo2_level)) + "% SPO"
                self.__has_been_connected__ = True

            spo2_ppm_texture = self.__font__.render(
                spo2_text, True, spo2_color, BLACK)

            heartbeat_texture = self.__font__.render(
                heartbeat_text, True, GREEN, BLACK)

            framebuffer.blit(
                spo2_ppm_texture, (self.__lhs__, self.__text_y_pos__))

            framebuffer.blit(
                heartbeat_texture, (self.__lhs__, self.__pulse_y_pos__))

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
