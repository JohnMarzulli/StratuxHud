from data_sources.ahrs_data import AhrsData
from rendering import colors
from views.abstract_elements.ahrs_element import AhrsElement


class TwoColumnTextInfoView(AhrsElement):
    ROW_TITLE_COLOR = colors.BLUE

    def uses_ahrs(self) -> bool:
        """
        The diagnostics page does not use AHRS.

        Returns:
            bool -- Always returns False.
        """

        return False

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False,
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__text_y_pos__ = framebuffer_size[1] - self.__font_height__
        self.__line_spacing__ = 1.01

    def __get_info_text__(self) -> list:
        return []

    def render(self, framebuffer, orientation: AhrsData):
        info_lines = self.__get_info_text__()

        if info_lines is None:
            return

        render_y = self.__top_border__ + self.__font_height__

        for line in info_lines:
            # Each line package is expected to be a tuple.
            # Index 0 is the left hand side
            # Index 1 is the right hand side

            self.__render_text__(
                framebuffer,
                line[0].text,
                [self.__left_border__, render_y],
                line[0].color,
            )

            # Draw the value in the encoded colors.
            self.__render_text__(
                framebuffer, line[1].text, [self.__center_x__, render_y], line[1].color
            )

            render_y = render_y + (self.__font_height__ * self.__line_spacing__)
