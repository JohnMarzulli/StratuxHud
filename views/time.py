from common_utils.task_timer import TaskProfiler
from data_sources.ahrs_data import AhrsData
from rendering import colors

from views import hud_elements
from views.ahrs_element import AhrsElement


class Time(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch,
        pixels_per_degree_y,
        font,
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__text_y_pos__ = self.__bottom_border__ - self.__font_height__

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        with TaskProfiler("views.time.Time.setup"):
            time_text = AhrsElement.GPS_UNAVAILABLE_TEXT

            if orientation.utc_time is not None:
                raw_text = str(orientation.utc_time)
                time_text = raw_text.split('.')[0]

                last_char = time_text[-1]
                if last_char.isdigit():
                    time_text += "Z"

        with TaskProfiler("views.time.Time.render"):
            self.__render_horizontal_centered_text__(
                framebuffer,
                time_text,
                [self.__center_x__, self.__text_y_pos__],
                colors.YELLOW)


if __name__ == '__main__':
    hud_elements.run_hud_element(Time, True)
