import math

import pygame

from common_utils.task_timer import TaskTimer
from data_sources.ahrs_data import AhrsData
from rendering import colors
from views.ahrs_element import AhrsElement
from views.hud_elements import run_ahrs_hud_element

TWO_PI = 2.0 * math.pi


class RollIndicatorText(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('RollIndicatorText')
        self.__roll_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        half_texture_height = int(font.get_height()) >> 1
        self.__font__ = font
        self.__text_y_pos__ = self.__center__[1] - half_texture_height

        for reference_angle in range(-180, 181):
            text = font.render(
                "{0:3}".format(int(math.fabs(reference_angle))),
                True,
                colors.WHITE,
                colors.BLACK)
            size_x, size_y = text.get_size()
            self.__roll_elements__[reference_angle] = (
                text, (size_x >> 1, size_y >> 1))

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()
        roll = int(orientation.roll)
        pitch = int(orientation.pitch)
        pitch_direction = ''
        if pitch > 0:
            pitch_direction = '+'
        attitude_text = "{0}{1:3} | {2:3}".format(pitch_direction, pitch, roll)

        roll_texture = self.__font__.render(
            attitude_text,
            True,
            colors.BLACK,
            colors.WHITE)
        texture_size = roll_texture.get_size()
        text_half_width, text_half_height = texture_size
        text_half_width = int(text_half_width / 2)
        framebuffer.blit(
            roll_texture,
            (self.__center__[0] - text_half_width, self.__text_y_pos__))
        self.task_timer.stop()


def wrap_angle(
    angle: float
) -> float:
    """
    Wraps an angle (degrees) to be between 0.0 and 360
    Arguments:
        angle {float} -- The input angle
    Returns: and value that is between 0 and 360, inclusive.
    """

    if angle < -360.0:
        return wrap_angle(angle + 360.0)

    if angle > 360.0:
        return wrap_angle(angle - 360.0)

    return angle


def wrap_radians(
    radians: float
) -> float:
    """
    Wraps an angle that is in radians to be between 0.0 and 2Pi
    Arguments:
        angle {float} -- The input angle
    Returns: and value that is between 0 and 2Pi, inclusive.
    """
    if radians < 0.0:
        return wrap_radians(radians + TWO_PI)

    if radians > TWO_PI:
        return wrap_angle(radians - TWO_PI)

    return radians


class RollIndicator(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('RollIndicator')
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        half_texture_height = int(font.get_height()) >> 1
        self.__font__ = font
        self.__text_y_pos__ = self.__center__[1] - half_texture_height
        self.arc_radius = int(framebuffer_size[1] / 3)
        self.top_arc_squash = 0.75
        self.arc_angle_adjust = math.pi / 8.0
        self.roll_indicator_arc_radians = 0.03
        self.arc_box = [self.__center__[0] - self.arc_radius, self.__center__[1] - (
            self.arc_radius / 2), self.arc_radius * 2, (self.arc_radius * 2) * self.top_arc_squash]
        self.reference_line_size = 20
        self.reference_arc_box = [self.arc_box[0],
                                  self.arc_box[1] - self.reference_line_size,
                                  self.arc_box[2],
                                  self.arc_box[3] - self.reference_line_size]
        self.smaller_reference_arc_box = [self.arc_box[0],
                                          self.arc_box[1] -
                                          (self.reference_line_size/2),
                                          self.arc_box[2],
                                          self.arc_box[3] - (self.reference_line_size/2)]
        self.half_pi = math.pi / 2.0

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        self.task_timer.start()

        roll_in_radians = math.radians(orientation.roll)

        # Draws the reference arc
        pygame.draw.arc(
            framebuffer,
            colors.GREEN,
            self.arc_box,
            self.arc_angle_adjust,
            math.pi - self.arc_angle_adjust,
            4)

        # Draw the important reference angles
        for roll_angle in [-30, -15, 15, 30]:
            reference_roll_in_radians = math.radians(roll_angle + 90.0)
            pygame.draw.arc(
                framebuffer,
                colors.GREEN,
                self.smaller_reference_arc_box,
                reference_roll_in_radians - self.roll_indicator_arc_radians,
                reference_roll_in_radians + self.roll_indicator_arc_radians,
                int(self.reference_line_size / 2))

        # Draw the REALLY important reference angles longer
        for roll_angle in [-90, -60, -45, 0, 45, 60, 90]:
            reference_roll_in_radians = math.radians(roll_angle + 90.0)
            pygame.draw.arc(
                framebuffer,
                colors.GREEN,
                self.reference_arc_box,
                reference_roll_in_radians - self.roll_indicator_arc_radians,
                reference_roll_in_radians + self.roll_indicator_arc_radians,
                self.reference_line_size)

        # Draws the current roll
        pygame.draw.arc(
            framebuffer,
            colors.YELLOW,
            self.arc_box,
            self.half_pi - roll_in_radians - self.roll_indicator_arc_radians,
            self.half_pi - roll_in_radians + self.roll_indicator_arc_radians,
            self.reference_line_size * 2)

        self.task_timer.stop()


if __name__ == '__main__':
    run_ahrs_hud_element(RollIndicator, False)
