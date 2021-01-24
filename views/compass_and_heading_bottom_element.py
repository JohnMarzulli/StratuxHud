from numbers import Number

import pygame
from data_sources.ahrs_data import AhrsData

from views.compass_and_heading_top_element import CompassAndHeadingTopElement
from views.hud_elements import *


class CompassAndHeadingBottomElement(CompassAndHeadingTopElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        CompassAndHeadingTopElement.__init__(
            self,
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size)

        self.__line_top__ = framebuffer_size[1] - self.line_height
        self.__line_bottom__ = framebuffer_size[1]
        self.heading_text_y = self.__line_top__ - (font.get_height() * 1.2)

        self._heading_box_y_ = framebuffer_size[1] - \
            int(font.get_height() * 2.8)
        self.compass_text_y = framebuffer_size[1] - \
            int(font.get_height())
        self.__border_width__ = 4
        text_height = font.get_height()
        border_vertical_size = (text_height >> 1) + (text_height >> 2)
        vertical_alignment_offset = int((border_vertical_size >> 1) + 0.5) \
            + self.__border_width__
        half_width = int(self.__heading_text__[360][1][0] * 3.5)
        self.__heading_text_box_lines__ = [
            [self.__center_x__ - half_width, self._heading_box_y_ -
                border_vertical_size + vertical_alignment_offset],
            [self.__center_x__ + half_width, self._heading_box_y_ -
                border_vertical_size + vertical_alignment_offset],
            [self.__center_x__ + half_width, self._heading_box_y_ +
                border_vertical_size + vertical_alignment_offset],
            [self.__center_x__ - half_width, self._heading_box_y_ + border_vertical_size + vertical_alignment_offset]]

    def __render_heading_mark__(
        self,
        framebuffer,
        x_pos: int,
        heading: int
    ):
        pygame.draw.line(
            framebuffer,
            colors.GREEN,
            [x_pos, self.__line_top__],
            [x_pos, self.__line_bottom__],
            self.__border_width__)

        self.__render_heading_text__(
            framebuffer,
            heading,
            x_pos,
            self.compass_text_y)

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

        if isinstance(heading, Number):
            heading = wrap_angle(heading)

            [self.__render_heading_mark__(
                framebuffer,
                heading_mark_to_render[0],
                heading_mark_to_render[1])
                for heading_mark_to_render in self.__heading_strip__[heading]]

        self.__render_hollow_heading_box__(
            orientation,
            framebuffer,
            self._heading_box_y_)


if __name__ == '__main__':
    run_ahrs_hud_element(CompassAndHeadingBottomElement)
