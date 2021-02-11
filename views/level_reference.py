"""
Draws a horizontal set of segments that work with the attitude indicator
to help create a level reference during flight.
"""

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
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

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

        self.level_reference_lines.append(artificial_horizon_level)
        self.level_reference_lines.append(left_hash)
        self.level_reference_lines.append(right_hash)

    def render(
        self,
        framebuffer,
        orientation
    ):
        """
        Renders a "straight and level" line to the HUD.
        """

        # pylint:disable=expression-not-assigned
        [drawing.segments(
            framebuffer,
            colors.WHITE,
            False,
            line,
            int(self.__line_width__ * 1.5)) for line in self.level_reference_lines]


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element
    run_ahrs_hud_element(LevelReference)
