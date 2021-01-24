from numbers import Number

from data_sources.ahrs_data import AhrsData
from rendering import colors

from views.ahrs_element import AhrsElement


class Altitude(AhrsElement):
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
        is_altitude_valid = orientation.alt is not None and isinstance(
            orientation.alt,
            Number)
        altitude_text = str(int(orientation.alt)) + \
            "' MSL" if is_altitude_valid else AhrsElement.INOPERATIVE_TEXT
        color = colors.WHITE if is_altitude_valid else colors.RED
        alt_texture = self.__font__.render(
            altitude_text,
            True,
            color,
            colors.BLACK)
        text_width, text_height = alt_texture.get_size()

        framebuffer.blit(
            alt_texture,
            (self.__right_border__ - text_width, self.__text_y_pos__))


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element

    run_ahrs_hud_element(Altitude)
