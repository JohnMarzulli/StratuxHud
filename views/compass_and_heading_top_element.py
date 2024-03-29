"""
Module to draw a compass and heading strip at the top of the screen.
"""

from numbers import Number

from common_utils import fast_math
from common_utils.task_timer import TaskProfiler
from data_sources.ahrs_data import AhrsData
from rendering import colors, drawing

from views.ahrs_element import AhrsElement
from views.hud_elements import apply_declination, run_hud_element


class CompassAndHeadingTopElement(AhrsElement):
    """
    Element to draw a compass and heading strip at the top of the screen.
    """

    def __get_mark_line_start__(
        self
    ) -> int:
        return self.__top_border__ + self.__font_height__

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
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__compass_box_y_position__ = self.__get_compass_y_position__()

        self.pixels_per_degree_x = framebuffer_size[0] / 360.0

        self.__heading_strip_offset__ = {}

        for heading in range(181):
            self.__heading_strip_offset__[heading] = int(
                self.pixels_per_degree_x * heading)

        self.__heading_strip__ = {}

        for heading in range(361):
            self.__heading_strip__[heading] = self.__generate_heading_strip__(heading)

        self.__heading_box_elements__ = self.__get_hollow_heading_box_elements__()

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
        offset = self.pixels_per_degree_x * apply_declination(1)
        x_pos += offset

        if x_pos < 0:
            x_pos = self.__width__ - x_pos

        if x_pos > self.__width__:
            x_pos -= self.__width__

        drawing.renderer.segment(
            framebuffer,
            colors.GREEN,
            [x_pos, self.__get_mark_line_start__()],
            [x_pos, self.__get_mark_line_end__()],
            self.__line_width__)

        self.__render_heading_text__(
            framebuffer,
            heading,
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

        with TaskProfiler("views.compass_and_heading_top_element.CompassAndHeadingTopElement.setup"):
            heading = orientation.get_onscreen_projection_heading()

            compass_heading = orientation.get_onscreen_compass_heading()
            gps_heading = orientation.get_onscreen_gps_heading()

            heading_text = "{0} | {1}".format(
                str(apply_declination(compass_heading)).rjust(3),
                str(apply_declination(gps_heading)).rjust(3))
            
            notation_text = "HDG       TRK"

        with TaskProfiler("views.compass_and_heading_top_element.CompassAndHeadingTopElement.render"):
            # pylint:disable=expression-not-assigned
            if not isinstance(heading, str):
                [self.__render_heading_mark__(
                    framebuffer,
                    heading_mark_to_render[0],
                    heading_mark_to_render[1]) for heading_mark_to_render in self.__heading_strip__[heading]]

            # Render the text that is showing our AHRS and GPS headings
            self.__render_hollow_heading_box__(
                [heading_text, notation_text],
                framebuffer)

    def __render_hollow_heading_box__(
        self,
        heading_text: list,
        framebuffer
    ):
        # pylint:disable=expression-not-assigned
        [box_element.render(framebuffer) for box_element in self.__heading_box_elements__]

        self.__render_horizontal_centered_text__(
            framebuffer,
            heading_text[0],
            [self.__center_x__, (self.__compass_box_y_position__ - (self.__font_half_height__ * 0.2))],
            colors.GREEN,
            colors.BLACK,
            0.8,
            not self.__reduced_visuals__)
        
        self.__render_horizontal_centered_text__(
            framebuffer,
            heading_text[1],
            [self.__center_x__, self.__compass_box_y_position__ + (self.__font_half_height__ * 1.2)],
            colors.GREEN,
            colors.BLACK,
            0.5,
            not self.__reduced_visuals__)

    def __get_hollow_heading_box_elements__(
        self
    ) -> list:
        heading_text_box_lines = self.__get_heading_box_points__(self.__compass_box_y_position__)

        return [
            drawing.FilledPolygon(
                heading_text_box_lines,
                colors.BLACK,
                False),
            drawing.HollowPolygon(
                heading_text_box_lines,
                colors.GREEN,
                self.__thin_line_width__)]

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
                colors.BLACK,
                1.0,
                not self.__reduced_visuals__)


if __name__ == '__main__':
    run_hud_element(CompassAndHeadingTopElement)
