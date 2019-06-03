from numbers import Number
from ahrs_element import AhrsElement
from lib.task_timer import TaskTimer
import hud_elements
import lib.display as display
import pygame
import utils
import testing
testing.load_imports()


class CompassAndHeadingTopElement(AhrsElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('CompassAndHeadingTopElement')
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.1
        self.__pixels_per_degree_y__ = pixels_per_degree_y

        self.heading_text_y = int(font.get_height())
        self.compass_text_y = int(font.get_height())

        self.pixels_per_degree_x = framebuffer_size[0] / 360.0
        cardinal_direction_line_proportion = 0.2
        self.line_height = int(
            framebuffer_size[1] * cardinal_direction_line_proportion)
        self.__font__ = font

        self.__heading_text__ = {}
        for heading in range(-1, 361):
            texture = self.__font__.render(
                str(heading), True, display.BLACK, display.YELLOW).convert()
            width, height = texture.get_size()
            self.__heading_text__[heading] = texture, (width >> 1, height >> 1)

        text_height = font.get_height()
        border_vertical_size = (text_height >> 1) + (text_height >> 2)
        half_width = int(self.__heading_text__[360][1][0] * 3.5)

        self.__center_x__ = self.__center__[0]

        self.__heading_text_box_lines__ = [
            [self.__center_x__ - half_width,
             self.compass_text_y + (1.5 * text_height) - border_vertical_size],
            [self.__center_x__ + half_width,
             self.compass_text_y + (1.5 * text_height) - border_vertical_size],
            [self.__center_x__ + half_width,
             self.compass_text_y + (1.5 * text_height) + border_vertical_size],
            [self.__center_x__ - half_width,
             self.compass_text_y + (1.5 * text_height) + border_vertical_size]]

        self.__heading_strip_offset__ = {}
        for heading in range(0, 181):
            self.__heading_strip_offset__[heading] = int(
                self.pixels_per_degree_x * heading)

        self.__heading_strip__ = {}

        for heading in range(0, 361):
            self.__heading_strip__[
                heading] = self.__generate_heading_strip__(heading)

        self.__render_heading_mark_timer__ = TaskTimer("HeadingRender")

    def __generate_heading_strip__(self, heading):
        things_to_render = []
        for heading_strip in self.__heading_strip_offset__:
            to_the_left = (heading - heading_strip)
            to_the_right = (heading + heading_strip)

            displayed_left = to_the_left
            displayed_right = to_the_right
            if to_the_left < 0:
                to_the_left += 360

            if to_the_right > 360:
                to_the_right -= 360

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

    def __render_heading_mark__(self, framebuffer, x_pos, heading):
        pygame.draw.line(framebuffer, display.GREEN,
                         [x_pos, self.line_height], [x_pos, 0], 4)

        self.__render_heading_text__(
            framebuffer,
            utils.apply_declination(heading),
            x_pos,
            self.compass_text_y)

    def render(self, framebuffer, orientation):
        """
        Renders the current heading to the HUD.
        """

        self.task_timer.start()

        # Render a crude compass
        # Render a heading strip along the top

        heading = orientation.get_onscreen_projection_heading()

        [self.__render_heading_mark__(framebuffer, heading_mark_to_render[0], heading_mark_to_render[1])
         for heading_mark_to_render in self.__heading_strip__[heading]]

        # Render the text that is showing our AHRS and GPS headings
        heading_y_pos = self.__font__.get_height() << 1
        self._render_hallow_heading_box_(orientation,
                                         framebuffer,
                                         heading_y_pos)
        self.task_timer.stop()

    def _render_hallow_heading_box_(self, orientation, framebuffer, heading_y_pos):
        heading_text = "{0} | {1}".format(
            str(utils.apply_declination(
                orientation.get_onscreen_projection_display_heading())).rjust(3),
            str(utils.apply_declination(
                orientation.get_onscreen_gps_heading())).rjust(3))

        rendered_text = self.__font__.render(
            heading_text, True, display.GREEN)
        text_width, text_height = rendered_text.get_size()

        framebuffer.blit(
            rendered_text, (self.__center_x__ - (text_width >> 1), heading_y_pos))

        pygame.draw.lines(framebuffer, display.GREEN, True,
                          self.__heading_text_box_lines__, 2)

    def __render_heading_text__(self, framebuffer, heading, position_x, position_y):
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
    import hud_elements
    hud_elements.run_ahrs_hud_element(CompassAndHeadingTopElement)
