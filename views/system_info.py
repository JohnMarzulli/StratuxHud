import math
import socket
import subprocess

from common_utils import fast_math, local_debug
from configuration import configuration
from data_sources.data_cache import HudDataCache
from rendering import colors

from views.two_column_text_info_view import TwoColumnTextInfoView
from views.text_line import TextLine

NORMAL_TEMP = 50
REDLINE_TEMP = 80

CO_SAFE = 10
CO_WARNING = 49

BATTERY_SAFE = 75
BATTERY_WARNING = 25

OFFLINE_TEXT = "Offline"
DISCONNECTED_TEXT = "DISCONNECTED"
DISABLED_TEXT = "DISABLED"


def get_ip_address() -> TextLine:
    """
    Returns the local IP address of this unit.

    Returns:
        tuple -- The IP address as a string and the color to render it in.
    """

    try:
        if local_debug.IS_LINUX and local_debug.IS_PI:
            ip_addr = subprocess.getoutput("hostname -I").strip()
            return TextLine(colors.GREEN, ip_addr)
        else:
            host_name = socket.gethostname()
            return TextLine(colors.GREEN, socket.gethostbyname(host_name))
    except:
        return TextLine(colors.RED, "UNKNOWN")


def get_cpu_temp_text_color(temperature: int) -> list:
    color = colors.GREEN

    if temperature > REDLINE_TEMP:
        color = colors.RED
    elif temperature > NORMAL_TEMP:
        delta = float(temperature - NORMAL_TEMP)
        temp_range = float(REDLINE_TEMP - NORMAL_TEMP)
        delta = fast_math.clamp(0.0, delta, temp_range)
        proportion = delta / temp_range
        color = colors.get_color_mix(colors.GREEN, colors.RED, proportion)

    return color


def get_cpu_temp() -> TextLine:
    """
    Gets the cpu temperature on RasPi (Celsius)

    Returns:
        string -- The CPU temp to display
    """

    color = colors.GREEN

    try:
        if local_debug.IS_LINUX:
            linux_cpu_temp = open("/sys/class/thermal/thermal_zone0/temp")
            temp = float(linux_cpu_temp.read())
            temp /= 1000

            color = get_cpu_temp_text_color(temp)

            return TextLine(color, "{0}C".format(int(math.floor(temp))))
    except:
        return TextLine(colors.GRAY, "---")

    return TextLine(colors.GRAY, "---")


def get_illyrian_spo2_color(spo2_level: int) -> tuple:
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


def get_aithre_co_color(co_ppm: int) -> tuple:
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


def get_aithre_battery_color(battery_percent: int) -> tuple:
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


class SystemInfo(TwoColumnTextInfoView):
    def uses_ahrs(self) -> bool:
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
        framebuffer_size,
        reduced_visuals: bool = False,
    ):
        super().__init__(
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size,
            reduced_visuals=reduced_visuals,
        )

        self.__update_ip_timer__ = 0
        self.__update_temp_timer__ = 0
        self.__ip_address__ = get_ip_address()
        self.__cpu_temp__ = None
        self.__line_spacing__ = 1.01

    def __get_info_text__(self):
        self.__update_ip_timer__ -= 1
        if self.__update_ip_timer__ <= 0:
            self.__ip_address__ = get_ip_address()
            self.__update_ip_timer__ = 120

        self.__update_temp_timer__ -= 1
        if self.__update_temp_timer__ <= 0:
            self.__cpu_temp__ = get_cpu_temp()
            self.__update_temp_timer__ = 60

        display_res_text = "{} x {}".format(
            self.__framebuffer_size__[0], self.__framebuffer_size__[1]
        )

        declination_color = (
            colors.GREEN
            if configuration.CONFIGURATION.is_declination_enabled()
            else colors.YELLOW
        )

        info_lines = [
            [
                TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, "VERSION"),
                TextLine(colors.GREEN, configuration.VERSION),
            ],
            [
                TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, "DISPLAY RES"),
                TextLine(colors.GREEN, display_res_text),
            ],
            [
                TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, "HUD CPU"),
                self.__cpu_temp__,
            ],
            [
                TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, "DECLINATION"),
                TextLine(declination_color, str(HudDataCache.DECLINATION)),
            ],
            [
                TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, "TRAFFIC"),
                TextLine(
                    colors.GREEN,
                    configuration.CONFIGURATION.get_traffic_manager_address(),
                ),
            ],
        ]

        addresses = self.__ip_address__.text.split(" ")
        for addr in addresses:
            info_lines.append(
                [
                    TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, "IP"),
                    TextLine(self.__ip_address__.color, addr),
                ]
            )

        return info_lines


if __name__ == "__main__":
    from views.hud_elements import run_hud_element

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    run_hud_element(SystemInfo)
