import datetime
import math
import socket
import subprocess

import pygame

from common_utils import local_debug, units
from common_utils.task_timer import TaskTimer
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.aithre import AithreClient
from data_sources.traffic import AdsbTrafficClient
from rendering import colors
from views.ahrs_element import AhrsElement
from views.hud_elements import run_ahrs_hud_element

NORMAL_TEMP = 50
REDLINE_TEMP = 80

CO_SAFE = 10
CO_WARNING = 49

BATTERY_SAFE = 75
BATTERY_WARNING = 25

OFFLINE_TEXT = "Offline"
DISCONNECTED_TEXT = "DISCONNECTED"
DISABLED_TEXT = "DISABLED"


def get_ip_address():
    """
    Returns the local IP address of this unit.

    Returns:
        tuple -- The IP address as a string and the color to render it in.
    """

    try:
        if local_debug.IS_LINUX and local_debug.IS_PI:
            ip_addr = subprocess.getoutput('hostname -I').strip()
            return (ip_addr, colors.GREEN)
        else:
            host_name = socket.gethostname()
            return (socket.gethostbyname(host_name), colors.GREEN)
    except:
        return ('UNKNOWN', colors.RED)


def get_cpu_temp_text_color(
    temperature: int
) -> list:
    color = colors.GREEN

    if temperature > REDLINE_TEMP:
        color = colors.RED
    elif temperature > NORMAL_TEMP:
        delta = float(temperature - NORMAL_TEMP)
        temp_range = float(REDLINE_TEMP - NORMAL_TEMP)
        delta = colors.clamp(0.0, delta, temp_range)
        proportion = delta / temp_range
        color = colors.get_color_mix(colors.GREEN, colors.RED, proportion)

    return color


def get_cpu_temp() -> str:
    """
    Gets the cpu temperature on RasPi (Celsius)

    Returns:
        string -- The CPU temp to display
    """

    color = colors.GREEN

    try:
        if local_debug.IS_LINUX:
            linux_cpu_temp = open('/sys/class/thermal/thermal_zone0/temp')
            temp = float(linux_cpu_temp.read())
            temp = temp/1000

            color = get_cpu_temp_text_color(temp)

            return ("{0}C".format(int(math.floor(temp))), color)
    except:
        return ('---', colors.GRAY)

    return ('---', colors.GRAY)


def get_illyrian_spo2_color(
    spo2_level: int
) -> tuple:
    """
    Gets the color for the SPO2 level
    """

    if isinstance(spo2_level, str):
        return colors.RED

    if spo2_level is None:
        return colors.RED

    color = colors.GREEN

    if spo2_level < 94:
        color = colors.YELLOW

    if spo2_level < 90:
        color = colors.RED

    return color


def get_aithre_co_color(
    co_ppm: int
) -> tuple:
    """
    Returns the color code for the carbon monoxide levels

    Arguments:
        co_ppm {int} -- Integer containing the Parts Per Million of CO

    Returns:
        color -- The color to display
    """
    color = colors.BLUE

    if isinstance(co_ppm, str):
        return colors.RED

    if co_ppm > CO_WARNING:
        color = colors.RED
    elif co_ppm > CO_SAFE:
        color = colors.YELLOW

    return color


def get_aithre_battery_color(
    battery_percent: int
) -> tuple:
    """
    Returns the color code for the Aithre battery level.

    Arguments:
        battery_percent {int} -- The percentage of battery.

    Returns:
        color -- The color to show the battery percentage in.
    """
    color = colors.RED

    if isinstance(battery_percent, str):
        return colors.RED

    if battery_percent >= BATTERY_SAFE:
        color = colors.GREEN
    elif battery_percent >= BATTERY_WARNING:
        color = colors.YELLOW

    return color


class SystemInfo(AhrsElement):
    def uses_ahrs(
        self
    ) -> bool:
        """
        The diagnostics page does not use AHRS.

        Returns:
            bool -- Always returns False.
        """

        return False

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
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

    def __get_aithre_text_and_color__(
        self
    ):
        """
        Gets the text and text color for the Aithre status.
        """

        if AithreClient.INSTANCE is None:
            return (DISCONNECTED_TEXT, colors.RED) if configuration.CONFIGURATION.aithre_enabled else (DISABLED_TEXT, colors.BLUE)

        co_report = AithreClient.INSTANCE.get_co_report()

        battery_text = 'UNK'
        battery_color = colors.RED

        try:
            battery = co_report.battery
            battery_suffix = "%"
            if isinstance(battery, str):
                battery_suffix = ""
            if battery is not None:
                battery_color = get_aithre_battery_color(battery)
                battery_text = "bat:{}{}".format(battery, battery_suffix)
        except Exception:
            battery_text = 'ERR'

        co_text = 'UNK'
        co_color = colors.RED

        try:
            co_ppm = co_report.co

            if co_ppm is not None and OFFLINE_TEXT not in co_ppm:
                co_text = 'co:{}ppm'.format(co_ppm)
                co_color = get_aithre_co_color(co_ppm)
        except Exception as ex:
            co_text = 'ERR'

        color = colors.RED if co_color is colors.RED or battery_color is colors.RED else \
            (colors.YELLOW if co_color is colors.YELLOW or battery_color is colors.YELLOW else colors.BLUE)

        return ('{} {}'.format(co_text, battery_text), color)

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()

        self.__update_ip_timer__ -= 1
        if self.__update_ip_timer__ <= 0:
            self.__ip_address__ = get_ip_address()
            self.__update_ip_timer__ = 120

        self.__update_temp_timer__ -= 1
        if self.__update_temp_timer__ <= 0:
            self.__cpu_temp__ = get_cpu_temp()
            self.__update_temp_timer__ = 60

        info_lines = [
            ["VERSION     : ", [configuration.VERSION, colors.YELLOW]],
            ["DECLINATION : ", [
                str(configuration.CONFIGURATION.get_declination()), colors.BLUE]],
            ["TRAFFIC     : ", [configuration.CONFIGURATION.get_traffic_manager_address(), colors.BLUE]]]

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
            self.__framebuffer_size__[0], self.__framebuffer_size__[1]), colors.BLUE]])

        render_y = self.__text_y_pos__

        for line in info_lines:
            # Draw the label in a standard color.
            texture_lhs = self.__font__.render(
                line[0], True, colors.BLUE, colors.BLACK)
            framebuffer.blit(texture_lhs, (0, render_y))
            size = texture_lhs.get_size()

            # Draw the value in the encoded colors.
            texture_rhs = self.__font__.render(
                line[1][0], True, line[1][1], colors.BLACK)
            framebuffer.blit(texture_rhs, (size[0], render_y))

            render_y = render_y - (self.font_height * self.__line_spacing__)

        self.task_timer.stop()


class Aithre(AhrsElement):
    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('Aithre')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y + (10 * text_half_height)
        self.__lhs__ = 0

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()

        if AithreClient.INSTANCE is not None and configuration.CONFIGURATION.aithre_enabled:
            co_level = AithreClient.INSTANCE.get_co_report()

            if (co_level.co is None and co_level.has_been_connected) or isinstance(co_level, str):
                co_color = colors.RED
                co_ppm_text = "OFFLINE"
            elif not co_level.has_been_connected:
                self.task_timer.stop()
                return
            else:
                co_color = get_aithre_co_color(co_level.co)
                units_text = "PPM" if co_level.is_connected else ""
                co_ppm_text = "{}{}".format(co_level.co, units_text)

            co_ppm_texture = self.__font__.render(
                co_ppm_text, True, co_color, colors.BLACK)

            framebuffer.blit(
                co_ppm_texture, (self.__lhs__, self.__text_y_pos__))
        self.task_timer.stop()


class Illyrian(AhrsElement):
    """
    Screen element to support the Illyrian blood/pulse oxymeter from Aithre
    """

    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('Illyrian')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y + (6 * text_half_height)
        self.__pulse_y_pos__ = center_y + (8 * text_half_height)
        self.__lhs__ = 0
        self.__has_been_connected__ = False

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()

        if AithreClient.INSTANCE is not None and configuration.CONFIGURATION.aithre_enabled:
            report = AithreClient.INSTANCE.get_spo2_report()
            spo2_level = report.spo2
            heartbeat = report.heartrate
            heartbeat_text = "{}BPM".format(heartbeat)

            if spo2_level is None or isinstance(spo2_level, str):
                if self.__has_been_connected__:
                    spo2_color = colors.RED
                    spo2_text = "OFFLINE"
                else:
                    self.task_timer.stop()
                    return
            else:
                spo2_color = get_illyrian_spo2_color(spo2_level)
                spo2_text = str(int(spo2_level)) + "% SPO"
                self.__has_been_connected__ = True

            spo2_ppm_texture = self.__font__.render(
                spo2_text, True, spo2_color, colors.BLACK)

            heartbeat_texture = self.__font__.render(
                heartbeat_text, True, colors.GREEN, colors.BLACK)

            framebuffer.blit(
                spo2_ppm_texture, (self.__lhs__, self.__text_y_pos__))

            framebuffer.blit(
                heartbeat_texture, (self.__lhs__, self.__pulse_y_pos__))

        self.task_timer.stop()


if __name__ == '__main__':
    run_ahrs_hud_element(Aithre)

if __name__ == '__main__':
    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    run_ahrs_hud_element(SystemInfo, True)
