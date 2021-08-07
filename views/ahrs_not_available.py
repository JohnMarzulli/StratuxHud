"""
Element to show that the AHRS data is not available from any source.
"""

from common_utils.task_timer import TaskProfiler
from data_sources.ahrs_data import AhrsData
from rendering import colors, drawing


class AhrsNotAvailable:
    """
    Element to show that the AHRS data is not available from any source.
    """

    # pylint:disable=unused-argument

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        width, height = framebuffer_size

        forwardslash = [[0, 0], [width, height]]
        backslash = [[0, height], [width, 0]]
        na_line_width = int(width * 0.02)

        self.__na_draw_commands__ = [
            drawing.Segment(
                forwardslash[0],
                forwardslash[1],
                colors.RED,
                na_line_width,
                True),
            drawing.Segment(
                backslash[0],
                backslash[1],
                colors.RED,
                na_line_width,
                True)]

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Render an "X" over the screen to indicate the AHRS is not
        available.
        """
        # pylint:disable=expression-not-assigned

        no_setup = TaskProfiler("views.ahrs_not_available.AhrsNotAvailable.setup")
        no_setup.start()
        no_setup.stop()

        with TaskProfiler("views.ahrs_not_available.AhrsNotAvailable.render"):
            [element.render(framebuffer) for element in self.__na_draw_commands__]


if __name__ == '__main__':
    from views.hud_elements import run_hud_element

    run_hud_element(AhrsNotAvailable)
