from datetime import datetime

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

        text_y_pos = self.__bottom_border__ - (self.__font_height__ << 1)

        self.__position__ = [self.__left_border__, text_y_pos]

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        if HudDataCache.IS_TRAFFIC_AVAILABLE:
            return

        current_time = datetime.utcnow()
        is_shown = (current_time.second % 2) == 0

        if not is_shown:
            return

        self.__render_text__(
            framebuffer,
            "ERROR: ADS-B IN",
            self.__position__,
            colors.RED,
            0.5)


if __name__ == '__main__':
    hud_elements.run_hud_element(TrafficNotAvailable, True)
