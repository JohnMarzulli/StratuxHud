"""
Module to draw a compass and heading strip at the bottom of the screen.
"""

from views.compass_and_heading_top_element import CompassAndHeadingTopElement
from views.hud_elements import run_hud_element


class CompassAndHeadingBottomElement(CompassAndHeadingTopElement):
    """
    Element to draw a compass and heading strip at the bottom of the screen.
    """

    def __get_mark_line_start__(
        self
    ) -> int:
        return self.__height__

    def __get_mark_line_end__(
        self
    ) -> int:
        return self.__bottom_border__ - self.__font_half_height__

    def __get_compass_y_position__(
        self
    ) -> int:
        return self.__bottom_border__ - int(self.__font_height__ * 1.5)

    def __get_heading_text_y_position__(
        self
    ) -> int:
        return self.__get_compass_y_position__()

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        CompassAndHeadingTopElement.__init__(
            self,
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size)


if __name__ == '__main__':
    run_hud_element(CompassAndHeadingBottomElement)
