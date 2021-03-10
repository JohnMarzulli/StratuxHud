"""
Element to show that the AHRS data is not available from any source.
"""

from data_sources.ahrs_data import AhrsData
from rendering import colors, drawing


class AhrsNotAvailable:
    """
    Element to show that the AHRS data is not available from any source.
    """

    # pylint:disable=unused-argument

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.__not_available_lines__ = []

        width, height = framebuffer_size

        self.__not_available_lines__.append([[0, 0], [width, height]])
        self.__not_available_lines__.append([[0, height], [width, 0]])
        self.__na_color__ = colors.RED
        self.__na_line_width__ = 20

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Render an "X" over the screen to indicate the AHRS is not
        available.
        """

        drawing.segment(
            framebuffer,
            self.__na_color__,
            self.__not_available_lines__[0][0],
            self.__not_available_lines__[0][1],
            self.__na_line_width__,
            True)
        drawing.segment(
            framebuffer,
            self.__na_color__,
            self.__not_available_lines__[1][0],
            self.__not_available_lines__[1][1],
            self.__na_line_width__,
            True)


if __name__ == '__main__':
    from views.hud_elements import run_hud_element

    run_hud_element(AhrsNotAvailable)
