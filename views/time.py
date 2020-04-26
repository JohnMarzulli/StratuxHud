import pygame

from common_utils.task_timer import TaskTimer
from data_sources.ahrs_data import AhrsData
from rendering import colors
from views.ahrs_element import AhrsElement


class Time(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch,
        pixels_per_degree_y,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('Time')
        self.__font__ = font
        font_height = font.get_height()
        text_half_height = int(font_height) >> 1
        self.__text_y_pos__ = framebuffer_size[1] - \
            text_half_height - font_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = int(framebuffer_size[0] * 0.01)
        self.__center_x__ = framebuffer_size[0] >> 1

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()

        time_text = str(orientation.utc_time).split('.')[0] \
            + "UTC" if orientation.utc_time is not None else AhrsElement.GPS_UNAVAILABLE_TEXT
        texture = self.__font__.render(
            time_text,
            True,
            colors.YELLOW,
            colors.BLACK)
        width = texture.get_size()[0]

        framebuffer.blit(
            texture,
            (self.__center_x__ - (width >> 1), self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(Time, True)
