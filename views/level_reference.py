"""
Draws a horizontal set of segments that work with the attitude indicator
to help create a level reference during flight.
"""

from common_utils.task_timer import TaskProfiler
from rendering import colors, drawing

from views.ahrs_element import AhrsElement

# pylint:disable=unused-argument


class LevelReference(AhrsElement):
    """
    Creates a set of horizontal segments to help define
    what is level flight.
    """

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.level_reference_lines = []

        width = framebuffer_size[0]

        edge_proportion = int(width * 0.05)

        artificial_horizon_level = [[int(width * 0.4),  self.__center__[1]],
                                    [int(width * 0.6),  self.__center__[1]]]
        left_hash = [[0, self.__center_y__], [
            edge_proportion, self.__center_y__]]
        right_hash = [
            [width - edge_proportion, self.__center_y__],
            [width, self.__center_y__]]

        line_width = int(self.__line_width__ * 1.5)

        self.__reference_segments__ = [
            drawing.Segment(
                artificial_horizon_level[0],
                artificial_horizon_level[1],
                colors.WHITE,
                line_width,
                False),
            drawing.Segment(
                left_hash[0],
                left_hash[1],
                colors.WHITE,
                line_width,
                False),
            drawing.Segment(
                right_hash[0],
                right_hash[1],
                colors.WHITE,
                line_width,
                False)]

    def render(
        self,
        framebuffer,
        orientation
    ):
        """
        Renders a "straight and level" line to the HUD.
        """

        no_setup = TaskProfiler("views.level_reference.LevelReference.setup")
        no_setup.start()
        no_setup.stop()

        # pylint:disable=expression-not-assigned
        with TaskProfiler("views.level_reference.LevelReference.render"):
            [segment.render(framebuffer) for segment in self.__reference_segments__]


if __name__ == '__main__':
    from views.hud_elements import run_hud_element
    run_hud_element(LevelReference)
