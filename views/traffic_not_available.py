from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from rendering import colors

from views import hud_elements
from views.ahrs_element import AhrsElement


class TrafficNotAvailable(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        self.__text_y_pos__ = int(self.__font_height__ * 0.7)

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
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


if __name__ == '__main__':
    hud_elements.run_ahrs_hud_element(TrafficNotAvailable, True)
