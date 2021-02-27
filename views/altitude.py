"""
Element to render the Altitude.
"""

from numbers import Number

from data_sources.ahrs_data import AhrsData
from rendering import colors

from views.ahrs_element import AhrsElement


def __get_indicated_text__(
    orientation: AhrsData,
    color: list
) -> list:
    """
    Get the text package (scale, text, color) for the given altitude.

    Args:
        orientation (AhrsData): [description]
        color (list): [description]

    Returns:
        list: A list of text packages that allow for the altitude
        and units to be drawn using vertical stacking.
    """
    is_altitude_valid = orientation.alt is not None and isinstance(
        orientation.alt,
        Number)

    text_package = []
    alt_value = str(int(orientation.alt)) \
        if is_altitude_valid else AhrsElement.INOPERATIVE_TEXT
    color = colors.WHITE if is_altitude_valid else colors.RED

    text_package.append(alt_value)
    text_package.append("ft " if is_altitude_valid else "   ")
    text_package.append("MSL")

    is_first = True
    text_with_scale_and_color = []

    for text_piece in text_package:
        scale = 1.0 if is_first else 0.5
        package = [scale, text_piece, color]

        text_with_scale_and_color.append(package)

        is_first = False

    return text_with_scale_and_color


class Altitude(AhrsElement):
    """
    Element to render the Altitude.
    """

    # pylint:disable=unused-argument
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        alt_y_pos = self.__center_y__ >> 1

        self.__text_y_pos__ = alt_y_pos - self.__font_half_height__

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Render the altitude to the framebuffer

        Args:
            framebuffer: The framebuffer/texture to render to.
            orientation (AhrsData): The current AHRS information for the aircraft.
        """
        is_altitude_valid = orientation.alt is not None and isinstance(
            orientation.alt,
            Number)
        color = colors.WHITE if is_altitude_valid else colors.RED
        annotated_text = __get_indicated_text__(orientation, color)
        self.__render_text_with_stacked_annotations_right_justified__(
            framebuffer,
            [self.__right_border__, self.__text_y_pos__],
            annotated_text)


if __name__ == '__main__':
    from views.hud_elements import run_hud_element

    run_hud_element(Altitude)
