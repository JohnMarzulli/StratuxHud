import display
import pygame
import math


class AhrsNotAvailable(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.__not_available_lines__ = []

        width, height = framebuffer_size

        self.__not_available_lines__.append([[0, 0], [width, height]])
        self.__not_available_lines__.append([[0, height], [width, 0]])
        self.__na_color__ = display.RED
        self.__na_line_width__ = 20

    def render(self, framebuffer, orientation):
        """
        Render an "X" over the screen to indicate the AHRS is not
        available.
        """

        pygame.draw.line(framebuffer, self.__na_color__, self.__not_available_lines__[
                         0][0], self.__not_available_lines__[0][1], self.__na_line_width__)
        pygame.draw.line(framebuffer, self.__na_color__, self.__not_available_lines__[
                         1][0], self.__not_available_lines__[1][1], self.__na_line_width__)


class LevelReference(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.level_reference_lines = []

        width = framebuffer_size[0]
        center = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)

        edge_reference_proportion = int(width * 0.05)

        artificial_horizon_level = [[int(width * 0.4),  center[1]],
                                    [int(width * 0.6),  center[1]]]
        left_hash = [[0, center[1]], [edge_reference_proportion, center[1]]]
        right_hash = [[width - edge_reference_proportion,
                       center[1]], [width, center[1]]]

        self.level_reference_lines.append(artificial_horizon_level)
        self.level_reference_lines.append(left_hash)
        self.level_reference_lines.append(right_hash)

    def render(self, framebuffer, orientation):
        """
        Renders a "straight and level" line to the HUD.
        """

        for line in self.level_reference_lines:
            pygame.draw.lines(framebuffer,
                              display.GRAY, False, line, 2)


class ArtificialHorizon(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.__pitch_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.1
        self.__pixels_per_degree_y__ = pixels_per_degree_y

        for reference_angle in range(-degrees_of_pitch, degrees_of_pitch + 1, 10):
            text = font.render(
                str(reference_angle), True, display.WHITE, display.BLACK)
            size_x, size_y = text.get_size()
            self.__pitch_elements__[reference_angle] = (
                text, (size_x >> 1, size_y >> 1))

        self.__sin_radians_by_degrees__ = {}
        self.__cos_radians_by_degrees__ = {}

        for degrees in range(-360, 361):
            radians = math.radians(degrees)
            self.__sin_radians_by_degrees__[degrees] = math.sin(radians)
            self.__cos_radians_by_degrees__[degrees] = math.cos(radians)

    def render(self, framebuffer, orientation):
        """
        Render the pitch hash marks.
        """

        for reference_angle in self.__pitch_elements__:
            line_coords, line_center = self.__get_line_coords__(
                int(orientation.pitch), int(orientation.roll), reference_angle)

            # Perform some trivial clipping of the lines
            # This also prevents early text rasterization
            if line_center[1] < 0 or line_center[1] > self.__framebuffer_size__[1]:
                continue

            pygame.draw.lines(framebuffer,
                              display.GREEN, False, line_coords, 2)

            text, half_size = self.__pitch_elements__[reference_angle]
            text = pygame.transform.rotate(text, orientation.roll)
            half_x, half_y = half_size
            center_x, center_y = line_center

            framebuffer.blit(text, (center_x - half_x, center_y - half_y))

    def __get_line_coords__(self, pitch=0, roll=0, hash_mark_angle=0):
        """
        Get the coordinate for the lines for a given pitch and roll.
        """

        if hash_mark_angle == 0:
            length = self.__long_line_width__
        else:
            length = self.__short_line_width__

        ahrs_center_x, ahrs_center_y = self.__center__
        pitch_offset = self.__pixels_per_degree_y__ * \
            (-pitch + hash_mark_angle)

        roll_delta = 90 - roll

        center_x = int(
            (ahrs_center_x - (pitch_offset * self.__cos_radians_by_degrees__[roll_delta])) + 0.5)
        center_y = int(
            (ahrs_center_y - (pitch_offset * self.__sin_radians_by_degrees__[roll_delta])) + 0.5)

        x_len = int((length * self.__cos_radians_by_degrees__[roll]) + 0.5)
        y_len = int((length * self.__sin_radians_by_degrees__[roll]) + 0.5)

        half_x_len = x_len >> 1
        half_y_len = y_len >> 1

        start_x = center_x - half_x_len
        end_x = center_x + half_x_len
        start_y = center_y + half_y_len
        end_y = center_y - half_y_len

        return [[start_x, start_y], [end_x, end_y]], (center_x, center_y)


class CompassAndHeading(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.1
        self.__pixels_per_degree_y__ = pixels_per_degree_y

        self.heading_text_y = int(font.get_height() * 2)
        self.compass_text_y = int(font.get_height() * 3.5)

        self.pixels_per_degree_x = framebuffer_size[0] / 360.0
        cardinal_direction_line_proportion = 0.05
        self.line_height = int(
            framebuffer_size[1] * cardinal_direction_line_proportion)
        self.__font__ = font

        self.__heading_text__ = {}
        for heading in range(-1, 361):
            self.__heading_text__[heading] = self.__font__.render(
                str(heading), True, display.GREEN, display.BLACK)

        text_height = font.get_height()
        border_vertical_size = (text_height >> 1) + (text_height >> 2)
        half_width = int(self.__heading_text__[360].get_size()[0] * 2.5)

        center_x = self.__center__[0]

        self.__heading_text_box_lines__ = [
            [center_x - half_width,
             self.compass_text_y - border_vertical_size],
            [center_x + half_width,
             self.compass_text_y - border_vertical_size],
            [center_x + half_width,
             self.compass_text_y + border_vertical_size],
            [center_x - half_width, self.compass_text_y + border_vertical_size]]

        self.__heading_strip__ = {}
        for heading in range(0, 181):
            self.__heading_strip__[heading] = int(
                self.pixels_per_degree_x * heading)

    def render(self, framebuffer, orientation):
        """
        Renders the current heading to the HUD.
        """
        compass = int(orientation.compass_heading)
        if compass is None or compass > 360 or compass < 0:
            compass = '---'

        # Render a crude compass
        # Render a heading strip along the top

        center_x = self.__center__[0]

        heading = int(orientation.get_heading())
        for heading_strip, position_x in self.__heading_strip__:
            to_the_left = (heading - heading_strip)
            to_the_right = (heading + heading_strip)

            if to_the_left < 0:
                to_the_left += 360

            if to_the_right > 360:
                to_the_right -= 360

            if (to_the_left % 90) == 0:
                line_x_left = center_x - position_x
                pygame.draw.line(framebuffer, display.GREEN,
                                 [line_x_left, self.line_height], [line_x_left, 0], 2)

                self.__render_heading__(
                    framebuffer, to_the_left, line_x_left, self.heading_text_y)

            if to_the_left == to_the_right:
                continue

            if (to_the_right % 90) == 0:
                line_x_right = center_x + position_x
                pygame.draw.lines(framebuffer, display.GREEN,
                                  [line_x_right, self.line_height], [line_x_right, 0], 2)

                self.__render_heading__(
                    framebuffer, to_the_right, line_x_right, self.heading_text_y)

        # Render the text that is showing our AHRS and GPS headings
        cover_old_rendering_spaces = "     "
        heading_text = "{0}{1} | {2}{0}".format(cover_old_rendering_spaces,
                                                compass, int(orientation.gps_heading))

        rendered_text = self.__font__.render(
            heading_text, True, display.GREEN, display.BLACK)
        text_width, text_height = rendered_text.get_size()

        framebuffer.blit(
            rendered_text, (center_x - (text_width >> 1), self.compass_text_y - (text_height >> 1)))

        pygame.draw.lines(framebuffer, display.GREEN, True,
                          self.__heading_text_box_lines__, 2)

    def __render_heading__(self, framebuffer, heading, position_x, position_y):
        """
        Renders the text with the results centered on the given
        position.
        """

        rendered_text = self.__heading_text__[heading]
        text_width, text_height = rendered_text.get_size()

        framebuffer.blit(
            rendered_text, (position_x - (text_width >> 1), position_y - (text_height >> 1)))

        return text_width, text_height
