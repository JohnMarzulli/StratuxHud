"""_summary_
View for Illyrian based devices.
"""

from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.aithre import AithreClient, Spo2Report
from rendering import colors
from views.abstract_elements.ahrs_element import AhrsElement
from views.system_info import get_illyrian_spo2_color


class Illyrian(AhrsElement):
    """
    Screen element to support the Illyrian blood/pulse oxymeter from Aithre
    """

    def uses_ahrs(self) -> bool:
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
        reduced_visuals: bool = False,
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__text_y_pos__ = self.__center_y__ + self.__font_height__
        self.__has_been_connected__ = False
        self.__text_scale__ = 0.5

    def __get_spo_text_package__(self, report: Spo2Report, device_number: int) -> list:
        text_packages = [
            [self.__text_scale__, "SPO2 ({}): ".format(device_number), colors.GREEN]
        ]

        if report is None:
            if self.__has_been_connected__:
                text_packages.append([self.__text_scale__, "OFFLINE", colors.RED])
            else:
                text_packages.append(
                    [self.__text_scale__, "NOT CONNECTED", colors.YELLOW]
                )
        else:
            color = get_illyrian_spo2_color(report.spo2)
            text_packages.append([self.__text_scale__, "●", color])

        return text_packages

    def render(self, framebuffer, orientation: AhrsData):
        if (
            AithreClient.INSTANCE is not None
            and configuration.CONFIGURATION.aithre_enabled
        ):
            y_pos = self.__text_y_pos__

            device_number = 1

            for report in AithreClient.INSTANCE.get_spo2_reports():
                report = AithreClient.INSTANCE.get_spo2_report()

                text_packages = self.__get_spo_text_package__(report, device_number)

                self.__render_text_with_stacked_annotations__(
                    framebuffer, [self.__left_border__, y_pos], text_packages
                )

                y_pos += self.__font_height__ * self.__text_scale__

                device_number += 1


if __name__ == "__main__":
    from views.hud_elements import run_hud_element

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    run_hud_element(Illyrian)
