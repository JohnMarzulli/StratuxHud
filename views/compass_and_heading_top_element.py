"""
Module to draw a compass and heading strip at the top of the screen.
"""

from numbers import Number

from common_utils import fast_math
from data_sources.ahrs_data import AhrsData
from rendering import drawing

from views.ahrs_element import AhrsElement
from views.hud_elements import apply_declination, colors, run_ahrs_hud_element


class CompassAndHeadingTopElement(AhrsElement):
    """
    Element to draw a compass and heading strip at the top of the screen.
    """

    def __get_mark_line_start__(
        self
    ) -> int:
        return 0

    def __get_mark_line_end__(
        self
    ) -> int:
        return self.__top_border__ + int(self.__font_height__ * 1.5)

    def __get_compass_y_position__(
        self
    ) -> int:
        return self.__top_border__ + int(self.__font_height__ >> 4)

    def __get_heading_text_y_position__(
        self
    ) -> int:
        return self.__get_compass_y_position__()

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        self.__compass_box_y_position__ = self.__get_compass_y_position__()

        self.pixels_per_degree_x = framebuffer_size[0] / 360.0

        self.__heading_text_box_lines__ = self.__get_heading_box_points__(
            self.__compass_box_y_position__)

        self.__heading_strip_offset__ = {}

        for heading in range(0, 181):
            self.__heading_strip_offset__[heading] = int(
                self.pixels_per_degree_x * heading)

        self.__heading_strip__ = {}

        for heading in range(0, 361):
            self.__heading_strip__[
                heading] = self.__generate_heading_strip__(heading)

    def __get_heading_box_points__(
        self,
        text_vertical_position: int
    ) -> list:
        border_vertical_size = self.__font_half_height__ >> 2
        half_width = int(self.__font_height__ * 2.5)

        left = self.__center_x__ - half_width
        right = self.__center_x__ + half_width
        top = text_vertical_position - border_vertical_size
        bottom = text_vertical_position + self.__font_height__ + border_vertical_size

        return [
            [left, top],
            [right, top],
            [right, bottom],
            [left, bottom]]

    def __generate_heading_strip__(
        self,
        heading: int
    ):
        things_to_render = []
        for heading_strip in self.__heading_strip_offset__:
            to_the_left = (heading - heading_strip)
            to_the_right = (heading + heading_strip)

            displayed_left = to_the_left
            displayed_right = to_the_right

            to_the_left = fast_math.wrap_degrees(to_the_left)
            to_the_right = fast_math.wrap_degrees(to_the_right)

            if (displayed_left == 0) or ((displayed_left % 90) == 0):
                line_x_left = self.__center_x__ - \
                    self.__heading_strip_offset__[heading_strip]
                things_to_render.append([line_x_left, to_the_left])

            if to_the_left == to_the_right:
                continue

            if (displayed_right % 90) == 0:
                line_x_right = self.__center_x__ + \
                    self.__heading_strip_offset__[heading_strip]
                things_to_render.append([line_x_right, to_the_right])

        return things_to_render

    def __render_heading_mark__(
        self,
        framebuffer,
        x_pos: int,
        heading: int
    ):
        drawing.segment(
            framebuffer,
            colors.GREEN,
            [x_pos, self.__get_mark_line_start__()],
            [x_pos, self.__get_mark_line_end__()],
            self.__line_width__)

        self.__render_heading_text__(
            framebuffer,
            apply_declination(heading),
            x_pos,
            self.__get_heading_text_y_position__())

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Renders the current heading to the HUD.
        """

        # Render a crude compass
        # Render a heading strip along the top

        heading = orientation.get_onscreen_projection_heading()

        [self.__render_heading_mark__(
            framebuffer,
            heading_mark_to_render[0],
            heading_mark_to_render[1])
            for heading_mark_to_render in self.__heading_strip__[heading]]

        # Render the text that is showing our AHRS and GPS headings
        self.__render_hollow_heading_box__(
            orientation,
            framebuffer)

    def __render_hollow_heading_box__(
        self,
        orientation: AhrsData,
        framebuffer
    ):
        heading_text = "{0} | {1}".format(
            str(apply_declination(
                orientation.get_onscreen_compass_heading())).rjust(3),
            str(apply_declination(
                orientation.get_onscreen_gps_heading())).rjust(3))

        drawing.polygon(
            framebuffer,
            colors.BLACK,
            self.__heading_text_box_lines__,
            False)

        drawing.segments(
            framebuffer,
            colors.GREEN,
            True,
            self.__heading_text_box_lines__,
            self.__thin_line_width__)

        self.__render_horizontal_centered_text__(
            framebuffer,
            heading_text,
            [self.__center_x__, self.__compass_box_y_position__],
            colors.GREEN,
            None,
            1.0,
            True)

    def __render_heading_text__(
        self,
        framebuffer,
        heading,
        position_x: int,
        position_y: int
    ):
        """
        Renders the text with the results centered on the given
        position.
        """
        if isinstance(heading, Number):
            heading = int(heading)

            self.__render_horizontal_centered_text__(
                framebuffer,
                str(heading),
                [position_x, position_y],
                colors.YELLOW,
                None,
                1.0,
                True)


if __name__ == '__main__':
    run_ahrs_hud_element(CompassAndHeadingTopElement)
