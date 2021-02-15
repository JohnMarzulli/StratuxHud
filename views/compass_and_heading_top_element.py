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
        return self.__top_border__ + self.__font_height__

    def __get_compass_y_position__(
        self
    ) -> int:
        return self.__top_border__ + int(self.__font_height__ >> 4)

    def __get_heading_text_y_position__(
        self
    ) -> int:
        return self.__get_mark_line_end__()

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

        self.__heading_text__ = self.__generate_heading_text__()

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

    def __generate_heading_text__(
        self
    ) -> dict:
        heading_text = {}

        for heading in range(-1, 360):
            texture = self.__font__.render(
                str(heading),
                True,
                colors.BLACK,
                colors.YELLOW).convert()
            width, height = texture.get_size()
            heading_text[heading] = texture, (width >> 1, height >> 1)

        return heading_text

    def __get_heading_box_points__(
        self,
        text_vertical_position: int
    ) -> list:
        border_vertical_size = self.__font_half_height__ >> 2
        half_width = int(self.__heading_text__[359][1][0] * 3.5)

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

        rendered_text = self.__font__.render(
            heading_text,
            True,
            colors.GREEN)
        text_width, text_height = rendered_text.get_size()

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
            self.__line_width__ >> 1)

        framebuffer.blit(
            rendered_text,
            (self.__center_x__ - (text_width >> 1), self.__compass_box_y_position__))

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
            rendered_text, half_size = self.__heading_text__[heading]

            framebuffer.blit(
                rendered_text, (position_x - half_size[0], position_y - half_size[1]))


if __name__ == '__main__':
    run_ahrs_hud_element(CompassAndHeadingTopElement)
