import pygame

from hud_elements import *
from lib.display import *
from lib.task_timer import TaskTimer


class ArtificialHorizon(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('ArtificialHorizon')
        self.__pitch_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.4
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__pixels_per_degree_y__ = pixels_per_degree_y
        self.__height__ = framebuffer_size[1]

        for reference_angle in range(-degrees_of_pitch, degrees_of_pitch + 1, 10):
            text = font.render(
                str(reference_angle), True, WHITE, BLACK).convert()
            size_x, size_y = text.get_size()
            self.__pitch_elements__[reference_angle] = (
                text, (size_x >> 1, size_y >> 1))

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        for reference_angle in self.__pitch_elements__:
            line_coords, line_center = self.__get_line_coords__(
                orientation.pitch, orientation.roll, reference_angle)

            # Perform some trivial clipping of the lines
            # This also prevents early text rasterization
            if line_center[1] < 0 or line_center[1] > self.__height__:
                continue

            pygame.draw.lines(framebuffer,
                              GREEN, False, line_coords, 4)

            text, half_size = self.__pitch_elements__[reference_angle]
            text = pygame.transform.rotate(text, orientation.roll)
            half_x, half_y = half_size
            center_x, center_y = line_center

            framebuffer.blit(text, (center_x - half_x, center_y - half_y))
        self.task_timer.stop()

    def __get_line_coords__(self, pitch, roll, reference_angle):
        """
        Get the coordinate for the lines for a given pitch and roll.
        """

        if reference_angle == 0:
            length = self.__long_line_width__
        else:
            length = self.__short_line_width__

        pitch = int(pitch)
        roll = int(roll)

        ahrs_center_x, ahrs_center_y = self.__center__
        pitch_offset = self.__pixels_per_degree_y__ * \
            (-pitch + reference_angle)

        roll_delta = 90 - roll

        center_x = int(
            (ahrs_center_x - (pitch_offset * COS_RADIANS_BY_DEGREES[roll_delta])) + 0.5)
        center_y = int(
            (ahrs_center_y - (pitch_offset * SIN_RADIANS_BY_DEGREES[roll_delta])) + 0.5)

        x_len = int((length * COS_RADIANS_BY_DEGREES[roll]) + 0.5)
        y_len = int((length * SIN_RADIANS_BY_DEGREES[roll]) + 0.5)

        half_x_len = x_len >> 1
        half_y_len = y_len >> 1

        start_x = center_x - half_x_len
        end_x = center_x + half_x_len
        start_y = center_y + half_y_len
        end_y = center_y - half_y_len

        return [[int(start_x), int(start_y)], [int(end_x), int(end_y)]], (int(center_x), int(center_y))

if __name__ == '__main__':
    run_hud_element(ArtificialHorizon)
