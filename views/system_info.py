import math
import socket
import subprocess
from numbers import Number

from common_utils import fast_math, local_debug
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.aithre import AithreClient, CoReport, Spo2Report
from data_sources.data_cache import HudDataCache
from rendering import colors

from views.ahrs_element import AhrsElement

NORMAL_TEMP = 50
REDLINE_TEMP = 80

CO_SAFE = 10
CO_WARNING = 49

BATTERY_SAFE = 75
BATTERY_WARNING = 25

OFFLINE_TEXT = "Offline"
DISCONNECTED_TEXT = "DISCONNECTED"
DISABLED_TEXT = "DISABLED"


class InfoText:
    def __init__(
        self,
        text: str,
        color: list
    ) -> None:
        self.text = text
        self.color = color


def get_ip_address() -> InfoText:
    """
    Returns the local IP address of this unit.

    Returns:
        tuple -- The IP address as a string and the color to render it in.
    """

    try:
        if local_debug.IS_LINUX and local_debug.IS_PI:
            ip_addr = subprocess.getoutput('hostname -I').strip()
            return InfoText(ip_addr, colors.GREEN)
        else:
            host_name = socket.gethostname()
            return InfoText(socket.gethostbyname(host_name), colors.GREEN)
    except:
        return InfoText('UNKNOWN', colors.RED)


def get_cpu_temp_text_color(
    temperature: int
) -> list:
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


def get_cpu_temp() -> InfoText:
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
            temp /= 1000

            color = get_cpu_temp_text_color(temp)

            return InfoText("{0}C".format(int(math.floor(temp))), color)
    except:
        return InfoText('---', colors.GRAY)

    return InfoText('---', colors.GRAY)


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


class TextInfoView(AhrsElement):
    ROW_TITLE_COLOR = colors.BLUE

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
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__text_y_pos__ = framebuffer_size[1] - self.__font_height__
        self.__update_ip_timer__ = 0
        self.__update_temp_timer__ = 0
        self.__ip_address__ = get_ip_address()
        self.__cpu_temp__ = None
        self.__line_spacing__ = 1.01

    def __get_info_text__(
        self
    ) -> list:
        return []

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        info_lines = self.__get_info_text__()

        if info_lines is None:
            return

        render_y = self.__top_border__ + self.__font_height__

        for line in info_lines:
            # Each line package is expected to be a tuple.
            # Index 0 is the left hand side
            # Index 1 is the right hand side

            self.__render_text__(
                framebuffer,
                line[0].text,
                [self.__left_border__, render_y],
                line[0].color)

            # Draw the value in the encoded colors.
            self.__render_text__(
                framebuffer,
                line[1].text,
                [self.__center_x__, render_y],
                line[1].color)

            render_y = render_y + (self.__font_height__ * self.__line_spacing__)


class AithreView(TextInfoView):
    STATUS_TEXT = "Aithre"
    ILLY_STATUS_TEXT = "Illyrian"
    CONNECTED_TEXT = "Connected"
    UNKNOWN_TEXT = "Unknown"
    BATTERY_TEXT = "Battery"
    CO_TEXT = "CO"

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size: list,
        reduced_visuals: bool
    ):
        super().__init__(degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, reduced_visuals=reduced_visuals)

    def __get_aithre_battery_info__(
        self,
        co_report
    ) -> list:
        battery_text = AithreView.UNKNOWN_TEXT
        battery_color = colors.RED

        try:
            battery = co_report.battery
            battery_suffix = "%"
            if isinstance(battery, str):
                battery_suffix = ""
            if battery is not None:
                battery_color = get_aithre_battery_color(battery)
                battery_text = "{}{}".format(battery, battery_suffix)
        except Exception:
            battery_text = 'ERR'

        return [
            InfoText(AithreView.BATTERY_TEXT, TextInfoView.ROW_TITLE_COLOR),
            InfoText(battery_text, battery_color)]

    def __get_aithre_co_info__(
        self,
        co_report
    ) -> list:
        co_text = AithreView.UNKNOWN_TEXT
        co_color = colors.RED

        try:
            co_ppm = co_report.co

            if co_ppm is not None and isinstance(co_ppm, Number):
                co_text = '{}ppm'.format(co_ppm)
                co_color = get_aithre_co_color(co_ppm)
        except:
            co_color = colors.RED
            co_text = 'ERR'

        return [
            InfoText(AithreView.CO_TEXT, TextInfoView.ROW_TITLE_COLOR),
            InfoText(co_text, co_color)]

    def __get_illyrian_text__(
        self
    ) -> list:
        if AithreClient.INSTANCE is None:
            return [
                InfoText(AithreView.ILLY_STATUS_TEXT, colors.BLUE),
                InfoText(DISCONNECTED_TEXT, colors.RED)]

        illy_status = []

        illyrians = AithreClient.INSTANCE.get_spo2_reports()

        if illyrians is None or len(illyrians) == 0:
            return [[
                InfoText("Illyrian", colors.BLUE),
                InfoText("Not Connected", colors.RED)
            ]]

        for spo2_report in illyrians:
            # $TODO - Write a subfunction that colors and encodes this.
            illy_status.append(
                [
                    InfoText("Illyrian", colors.BLUE),
                    InfoText(
                        "{}% / {}bpm".format(
                            spo2_report.spo2,
                            spo2_report.heartrate),
                        colors.GREEN)
                ]
            )

        return illy_status

    def __get_aithre_info_text(
        self
    ) -> list:
        if AithreClient.INSTANCE is None:
            current_status = InfoText(DISCONNECTED_TEXT, colors.RED) if configuration.CONFIGURATION.aithre_enabled else InfoText(DISABLED_TEXT, colors.BLUE)

            return [
                InfoText(AithreView.STATUS_TEXT, colors.BLUE),
                current_status]

        co_report = AithreClient.INSTANCE.get_co_report()

        is_connected = co_report.has_been_connected and co_report.is_connected

        status_text = AithreView.CONNECTED_TEXT if is_connected else DISCONNECTED_TEXT
        status_color = colors.GREEN if is_connected else colors.RED

        return [
            [InfoText(AithreView.STATUS_TEXT, TextInfoView.ROW_TITLE_COLOR), InfoText(status_text, status_color)],
            self.__get_aithre_battery_info__(co_report),
            self.__get_aithre_co_info__(co_report)]

    def __get_info_text__(
        self
    ) -> list:
        aithre_info_text = self.__get_aithre_info_text()
        illy_info_text = self.__get_illyrian_text__()

        return aithre_info_text + illy_info_text


class SystemInfo(TextInfoView):
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
        framebuffer_size,
        reduced_visuals: bool
    ):
        super().__init__(degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, reduced_visuals=reduced_visuals)

        self.__update_ip_timer__ = 0
        self.__update_temp_timer__ = 0
        self.__ip_address__ = get_ip_address()
        self.__cpu_temp__ = None
        self.__line_spacing__ = 1.01

    def __get_info_text__(
        self
    ):
        self.__update_ip_timer__ -= 1
        if self.__update_ip_timer__ <= 0:
            self.__ip_address__ = get_ip_address()
            self.__update_ip_timer__ = 120

        self.__update_temp_timer__ -= 1
        if self.__update_temp_timer__ <= 0:
            self.__cpu_temp__ = get_cpu_temp()
            self.__update_temp_timer__ = 60

        display_res_text = "{} x {}".format(self.__framebuffer_size__[0], self.__framebuffer_size__[1])

        declination_color = colors.GREEN if configuration.CONFIGURATION.is_declination_enabled() else colors.YELLOW

        info_lines = [
            [InfoText("VERSION", TextInfoView.ROW_TITLE_COLOR), InfoText(configuration.VERSION, colors.GREEN)],
            [InfoText("DISPLAY RES", TextInfoView.ROW_TITLE_COLOR), InfoText(display_res_text, colors.GREEN)],
            [InfoText("HUD CPU", TextInfoView.ROW_TITLE_COLOR), self.__cpu_temp__],
            [InfoText("DECLINATION", TextInfoView.ROW_TITLE_COLOR), InfoText(str(HudDataCache.DECLINATION), declination_color)],
            [InfoText("TRAFFIC", TextInfoView.ROW_TITLE_COLOR), InfoText(configuration.CONFIGURATION.get_traffic_manager_address(), colors.GREEN)]]

        addresses = self.__ip_address__.text.split(' ')
        for addr in addresses:
            info_lines.append([InfoText("IP", TextInfoView.ROW_TITLE_COLOR), InfoText(addr, self.__ip_address__.color)])

        return info_lines


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
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__text_y_pos__ = self.__center_y__ + self.__font_half_height__

    def __get_co_text_package__(
        self,
        report: CoReport
    ) -> list:
        levels = "OFFLINE"
        co_color = colors.RED

        if report is None or not report.has_been_connected:
            return []

        if report.is_connected and not isinstance(report, str) and not isinstance(report.co, str):
            co_color = get_aithre_co_color(report.co)
            levels = "{} PPM".format(report.co)

        text_scale = 0.5
        return [[text_scale, "CO : {}".format(levels), co_color]]

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        if AithreClient.INSTANCE is not None and configuration.CONFIGURATION.aithre_enabled:
            co_level = AithreClient.INSTANCE.get_co_report()

            text = self.__get_co_text_package__(co_level)

            if text is not None and len(text) > 0:
                self.__render_text_with_stacked_annotations__(
                    framebuffer,
                    [self.__left_border__, self.__text_y_pos__],
                    text)


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
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__text_y_pos__ = self.__center_y__ + self.__font_height__
        self.__has_been_connected__ = False
        self.__text_scale__ = 0.5

    def __get_spo_text_package__(
        self,
        report: Spo2Report,
        device_number: int
    ) -> list:
        text_packages = [[self.__text_scale__, "SPO2 ({}): ".format(device_number), colors.GREEN]]

        if report is None:
            if self.__has_been_connected__:
                text_packages.append([self.__text_scale__, "OFFLINE", colors.RED])
            else:
                text_packages.append([self.__text_scale__, "NOT CONNECTED", colors.YELLOW])
        else:
            color = get_illyrian_spo2_color(report.spo2)
            text_packages.append([self.__text_scale__, "●", color])

        return text_packages

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        if AithreClient.INSTANCE is not None and configuration.CONFIGURATION.aithre_enabled:
            y_pos = self.__text_y_pos__

            device_number = 1

            for report in AithreClient.INSTANCE.get_spo2_reports():
                report = AithreClient.INSTANCE.get_spo2_report()

                text_packages = self.__get_spo_text_package__(report, device_number)

                self.__render_text_with_stacked_annotations__(
                    framebuffer,
                    [self.__left_border__, y_pos],
                    text_packages)

                y_pos += (self.__font_height__ * self.__text_scale__)

                device_number += 1


if __name__ == '__main__':
    from views.hud_elements import run_hud_element

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    run_hud_element(SystemInfo, True)
