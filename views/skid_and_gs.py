"""
View element for a g-meter
"""

from numbers import Number

from common_utils.local_debug import IS_SLOW
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

        self.__skid_ball_radius__ = self.__height__ * 0.04
        self.__skid_centering_line_length__ = int(
            self.__skid_ball_radius__ * 1.3)

        self.__skid_top_edge__ = self.__skid_y_center__ - \
            self.__skid_centering_line_length__
        self.__skid_bottom_edge__ = self.__skid_y_center__ + \
            self.__skid_centering_line_length__
        self.__skid_left_edge__ = self.__center_x__ - \
            self.__skid_ball_radius__ - self.__skid_range__
        self.__skid_right_edge__ = self.__center_x__ + \
            self.__skid_ball_radius__ + self.__skid_range__

        self.__skid_range_box__ = [
            [self.__skid_left_edge__, self.__skid_top_edge__],
            [self.__skid_right_edge__, self.__skid_top_edge__],
            [self.__skid_right_edge__, self.__skid_bottom_edge__],
            [self.__skid_left_edge__, self.__skid_bottom_edge__]]

        self.__ball_center_range__ = int(self.__skid_ball_radius__ + 0.5) + 1

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

        # Draw a box that shows the range of the ball
        drawing.polygon(
            framebuffer,
            colors.DARK_GRAY,
            self.__skid_range_box__,
            False)

        # Draw the skid ball
        screen_x = self.__center_x__ + \
            int(self.__skid_range__ * orientation.slip_skid * 3.0)

        screen_x = max(screen_x, self.__skid_left_edge__)
        screen_x = min(self.__skid_right_edge__, screen_x)

        if not IS_SLOW:
            drawing.filled_circle(
                framebuffer,
                colors.BLACK,
                [screen_x, self.__skid_y_center__],
                int(self.__skid_ball_radius__ + self.__thin_line_width__))

        drawing.filled_circle(
            framebuffer,
            colors.YELLOW,
            [screen_x, self.__skid_y_center__],
            int(self.__skid_ball_radius__))

        # Draw edges that define center last
        # so it looks like the ball passes behind them
        left_x = self.__center_x__ - self.__ball_center_range__
        right_x = self.__center_x__ + self.__ball_center_range__

        for x_pos in [left_x, right_x]:
            if not IS_SLOW:
                drawing.segment(
                    framebuffer,
                    colors.BLACK,
                    [x_pos, self.__skid_top_edge__],
                    [x_pos, self.__skid_bottom_edge__],
                    self.__thick_line_width__ << 2)

            drawing.segment(
                framebuffer,
                colors.WHITE,
                [x_pos, self.__skid_top_edge__],
                [x_pos, self.__skid_bottom_edge__],
                self.__line_width__)

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
    from views.hud_elements import run_hud_element
    run_hud_element(SkidAndGs)
