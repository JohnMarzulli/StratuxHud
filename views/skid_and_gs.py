from numbers import Number

from data_sources.ahrs_data import AhrsData
from rendering import colors

from views.ahrs_element import AhrsElement


class SkidAndGs(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)
        g_y_pos = self.__center_y__ >> 1

        self.__text_y_pos__ = (self.__font_half_height__ << 2) + \
            g_y_pos - self.__font_half_height__

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        is_valid = isinstance(orientation.g_load, Number)
        g_load_text = "{0:.1f} Gs".format(
            orientation.g_load) if is_valid else orientation.g_load
        texture = self.__font__.render(
            g_load_text,
            True,
            colors.WHITE if is_valid else colors.RED,
            colors.BLACK)
        text_width, text_height = texture.get_size()

        framebuffer.blit(
            texture,
            (self.__right_border__ - text_width, self.__text_y_pos__))


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element
    run_ahrs_hud_element(SkidAndGs)
