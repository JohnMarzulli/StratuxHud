from numbers import Number

from configuration import configuration
from data_sources.aithre import AithreClient
from rendering import colors
from views.abstract_elements.text_line import TextLine
from views.abstract_elements.two_column_text_info_view import TwoColumnTextInfoView
from views.system_info import (
    DISABLED_TEXT,
    DISCONNECTED_TEXT,
    get_aithre_battery_color,
    get_aithre_co_color,
)


class AithreView(TwoColumnTextInfoView):
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

    def __get_aithre_battery_info__(self, co_report) -> list:
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
            battery_text = "ERR"

        return [
            TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, AithreView.BATTERY_TEXT),
            TextLine(battery_color, battery_text),
        ]

    def __get_aithre_co_info__(self, co_report) -> list:
        co_text = AithreView.UNKNOWN_TEXT
        co_color = colors.RED

        try:
            co_ppm = co_report.co

            if co_ppm is not None and isinstance(co_ppm, Number):
                co_text = "{}ppm".format(co_ppm)
                co_color = get_aithre_co_color(co_ppm)
        except:
            co_color = colors.RED
            co_text = "ERR"

        return [
            TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, AithreView.CO_TEXT),
            TextLine(co_color, co_text),
        ]

    def __get_illyrian_text__(self) -> list:
        if AithreClient.INSTANCE is None:
            return [
                TextLine(colors.BLUE, AithreView.ILLY_STATUS_TEXT),
                TextLine(colors.RED, DISCONNECTED_TEXT),
            ]

        illy_status = []

        illyrians = AithreClient.INSTANCE.get_spo2_reports()

        if illyrians is None or len(illyrians) == 0:
            return [
                [
                    TextLine(colors.BLUE, "Illyrian"),
                    TextLine(colors.RED, "Not Connected"),
                ]
            ]

        for spo2_report in illyrians:
            # $TODO - Write a subfunction that colors and encodes this.
            illy_status.append(
                [
                    TextLine(colors.BLUE, "Illyrian"),
                    TextLine(
                        colors.GREEN,
                        "{}% / {}bpm".format(spo2_report.spo2, spo2_report.heartrate),
                    ),
                ]
            )

        return illy_status

    def __get_aithre_info_text(self) -> list:
        if AithreClient.INSTANCE is None:
            current_status = (
                TextLine(colors.RED, DISCONNECTED_TEXT)
                if configuration.CONFIGURATION.aithre_enabled
                else TextLine(colors.BLUE, DISABLED_TEXT)
            )

            return [TextLine(colors.BLUE, AithreView.STATUS_TEXT), current_status]

        co_report = AithreClient.INSTANCE.get_co_report()

        is_connected = co_report.has_been_connected and co_report.is_connected

        status_text = AithreView.CONNECTED_TEXT if is_connected else DISCONNECTED_TEXT
        status_color = colors.GREEN if is_connected else colors.RED

        return [
            [
                TextLine(TwoColumnTextInfoView.ROW_TITLE_COLOR, AithreView.STATUS_TEXT),
                TextLine(status_color, status_text),
            ],
            self.__get_aithre_battery_info__(co_report),
            self.__get_aithre_co_info__(co_report),
        ]

    def __get_info_text__(self) -> list:
        aithre_info_text = self.__get_aithre_info_text()
        illy_info_text = self.__get_illyrian_text__()

        return aithre_info_text + illy_info_text


if __name__ == "__main__":
    from views.hud_elements import run_hud_element

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    run_hud_element(AithreView)
