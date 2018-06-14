import pygame

import display
from compass_and_heading_top_element import CompassAndHeadingTopElement
from lib.task_timer import TaskTimer


class CompassAndHeadingBottomElement(CompassAndHeadingTopElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        CompassAndHeadingTopElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size)
        self.task_timer = TaskTimer('CompassAndHeadingBottomElement')
        self.__line_top__ = framebuffer_size[1] - self.line_height
        self.__line_bottom__ = framebuffer_size[1]
        self.heading_text_y = self.__line_top__ - (font.get_height() * 1.2)

        self.compass_text_y = framebuffer_size[1] - \
            int(font.get_height() * 2)
        self.__border_width__ = 4
        text_height = font.get_height()
        border_vertical_size = (text_height >> 1) + (text_height >> 2)
        vertical_alignment_offset = int(
            (border_vertical_size / 2.0) + 0.5) + self.__border_width__
        half_width = int(self.__heading_text__[360][1][0] * 3.5)
        self.__heading_text_box_lines__ = [
            [self.__center_x__ - half_width,
             self.compass_text_y - border_vertical_size + vertical_alignment_offset],
            [self.__center_x__ + half_width,
             self.compass_text_y - border_vertical_size + vertical_alignment_offset],
            [self.__center_x__ + half_width,
             self.compass_text_y + border_vertical_size + vertical_alignment_offset],
            [self.__center_x__ - half_width, self.compass_text_y + border_vertical_size + vertical_alignment_offset]]

    def __render_heading_mark__(self, framebuffer, x_pos, heading):
        pygame.draw.line(framebuffer, display.GREEN,
                         [x_pos, self.__line_top__], [x_pos, self.__line_bottom__], self.__border_width__)

        self.__render_heading_text__(
            framebuffer, heading, x_pos, self.compass_text_y)

    def render(self, framebuffer, orientation):
        """
        Renders the current heading to the HUD.
        """

        self.task_timer.start()

        # Render a crude compass
        # Render a heading strip along the top

        heading = orientation.get_onscreen_projection_heading()

        if heading < 0:
            heading += 360

        if heading > 360:
            heading -= 360

        for heading_mark_to_render in self.__heading_strip__[heading]:
            self.__render_heading_mark__(
                framebuffer, heading_mark_to_render[0], heading_mark_to_render[1])

        # Render the text that is showing our AHRS and GPS headings
        heading_text = "{0} | {1}".format(
            orientation.get_onscreen_projection_display_heading(), int(orientation.gps_heading))

        rendered_text = self.__font__.render(
            heading_text, True, display.BLACK, display.GREEN)
        text_width, text_height = rendered_text.get_size()

        pygame.draw.polygon(framebuffer, display.GREEN,
                            self.__heading_text_box_lines__)

        framebuffer.blit(
            rendered_text, (self.__center_x__ - (text_width >> 1), self.compass_text_y))
        self.task_timer.stop()
