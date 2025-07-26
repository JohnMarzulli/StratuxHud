from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.aithre import AithreClient, CoReport
from rendering import colors
from views.abstract_elements.ahrs_element import AhrsElement
from views.system_info import get_aithre_co_color

"""
Recommended view:

{
    "elements": [
    "AithreInfo"
    ],
    "name": "Aithre"
}
"""

class Aithre(AhrsElement):
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

        self.__text_y_pos__ = self.__center_y__ + self.__font_half_height__

    def __get_co_text_package__(self, report: CoReport) -> list:
        levels = "OFFLINE"
        co_color = colors.RED

        if report is None or not report.has_been_connected:
            return []

        if (
            report.is_connected
            and not isinstance(report, str)
            and not isinstance(report.co, str)
        ):
            co_color = get_aithre_co_color(report.co)
            levels = "{} PPM".format(report.co)

        text_scale = 0.5
        return [[text_scale, "CO : {}".format(levels), co_color]]

    def render(self, framebuffer, orientation: AhrsData):
        if (
            AithreClient.INSTANCE is not None
            and configuration.CONFIGURATION.aithre_enabled
        ):
            co_level = AithreClient.INSTANCE.get_co_report()

            text = self.__get_co_text_package__(co_level)

            if text is not None and len(text) > 0:
                self.__render_text_with_stacked_annotations__(
                    framebuffer, [self.__left_border__, self.__text_y_pos__], text
                )


if __name__ == "__main__":
    from views.hud_elements import run_hud_element

    # for temp in range(45, 95, 5):
    #     color = get_cpu_temp_text_color(temp)
    #     print("{3} => {0},{1},{2}".format(color[0], color[1], color[2], temp))

    run_hud_element(Aithre)
