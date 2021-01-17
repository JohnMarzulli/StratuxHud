from numbers import Number

from common_utils.task_timer import TaskTimer
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
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = (text_half_height << 2) + \
            center_y - text_half_height
        self.__rhs__ = int(framebuffer_size[0])  # was 0.9

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
            (self.__rhs__ - text_width, self.__text_y_pos__))


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element
    run_ahrs_hud_element(SkidAndGs)
