import pygame

from common_utils import local_debug, units
from common_utils.task_timer import TaskTimer
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from rendering import colors
from views.ahrs_element import AhrsElement


class TrafficNotAvailable(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('TrafficNotAvailable')
        self.__font__ = font
        font_height = font.get_height()
        self.__text_y_pos__ = int(font_height * 0.7)
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = int(framebuffer_size[0] * 0.01)
        self.__center_x__ = framebuffer_size[0] >> 1

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()

        if not HudDataCache.IS_TRAFFIC_AVAILABLE:
            (texture, size) = HudDataCache.get_cached_text_texture(
                "TRAFFIC UNAVAILABLE",
                self.__font__,
                text_color=colors.RED,
                background_color=colors.BLACK,
                use_alpha=True)
            width = size[0]

            framebuffer.blit(
                texture,
                (self.__center_x__ - (width >> 1), self.__text_y_pos__))
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(TrafficNotAvailable, True)
