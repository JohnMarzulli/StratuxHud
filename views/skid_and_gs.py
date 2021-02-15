"""
View element for a g-meter
"""

from numbers import Number

from data_sources.ahrs_data import AhrsData
from rendering import colors, drawing

from views.ahrs_element import AhrsElement


class SkidAndGs(AhrsElement):
    """
    View element for a g-meter
    """

    # pylint:disable=unused-argument
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

        self.__skid_y_center__ = int(self.__height__ * .7)
        self.__skid_range__ = self.__width__ >> 4

    def __render_g_loading__(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Renders the current G load, minimum, and maximum

        Args:
            framebuffer: The surface to draw to.
            orientation (AhrsData): The current flight data
        """
        is_valid = isinstance(orientation.g_load, Number)
        g_load_text = "{0:.1f}G".format(
            orientation.g_load) if is_valid else orientation.g_load

        min_g_text = "{0:.1f}".format(orientation.min_g)
        max_g_text = "{0:.1f}".format(orientation.max_g)

        text_package = [
            [1.0, g_load_text, colors.WHITE if is_valid else colors.RED],
            [0.5, min_g_text, colors.WHITE],
            [0.5, max_g_text, colors.WHITE]]

        self.__render_text_with_stacked_annotations_right_justified__(
            framebuffer,
            [self.__right_border__, self.__text_y_pos__],
            text_package)

    def __render_skid_ball__(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        if orientation.slip_skid is None \
                or isinstance(orientation.slip_skid, str):
            return

        ball_radius = self.__height__ * 0.03
        line_length = int(ball_radius * 1.3)

        top_edge = self.__skid_y_center__ - line_length
        bottom_edge = self.__skid_y_center__ + line_length
        left_edge = self.__center_x__ - ball_radius - self.__skid_range__
        right_edge = self.__center_x__ + ball_radius + self.__skid_range__

        # Draw a centering line.
        drawing.segment(
            framebuffer,
            colors.WHITE,
            [self.__center_x__, top_edge],
            [self.__center_x__, bottom_edge],
            self.__line_width__)

        # Draw the edges
        drawing.segment(
            framebuffer,
            colors.WHITE,
            [left_edge, top_edge],
            [left_edge, bottom_edge],
            self.__line_width__)

        drawing.segment(
            framebuffer,
            colors.WHITE,
            [right_edge, top_edge],
            [right_edge, bottom_edge],
            self.__line_width__)

        screen_x = self.__center_x__ + \
            int(self.__skid_range__ * orientation.slip_skid)

        drawing.filled_circle(
            framebuffer,
            colors.YELLOW,
            [screen_x, self.__skid_y_center__],
            int(ball_radius))

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Renders the current G load, minimum, and maximum

        Args:
            framebuffer: The surface to draw to.
            orientation (AhrsData): The current flight data
        """
        self.__render_g_loading__(framebuffer, orientation)
        self.__render_skid_ball__(framebuffer, orientation)


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element
    run_ahrs_hud_element(SkidAndGs)
