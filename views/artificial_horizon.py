import pygame
from data_sources.ahrs_data import AhrsData

from views.ahrs_element import AhrsElement
from views.hud_elements import *


class ArtificialHorizon(AhrsElement):
    def __generate_reference_angle__(
        self,
        reference_angle: int
    ):
        """
        Renders the text for the reference angle.

        Arguments:
            reference_angle {int} -- The angle that we are going to produce text for.

        Returns:
            (Surface, (int, int)) -- Tuple of the texture and the half size x & y.
        """

        text = self.__font__.render(
            str(reference_angle),
            False,
            colors.WHITE,
            colors.BLACK).convert()
        size_x, size_y = text.get_size()

        return (text, (size_x >> 1, size_y >> 1))

    def __generate_rotated_reference_angle__(
        self,
        reference_angle: float
    ):
        """
        Returns the text for the reference angle rotated.

        Arguments:
            reference_angle {int} -- The angle marking to generate the textures for.

        Returns:
            ({int, Surface}, (int, int)) -- A map of the textures keyed by roll angle and the half size of the texture.
        """

        rotate = pygame.transform.rotate
        reference_angle, half_size = self.__generate_reference_angle__(
            reference_angle)
        rotated_angles = {roll: rotate(reference_angle, roll)
                          for roll in range(-45, 46, 1)}

        # Make sure that the un-rolled version is the original
        # so as to not have any artifacts for later rotations
        # that get added.
        rotated_angles[0] = reference_angle

        return rotated_angles, half_size

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.4
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__pixels_per_degree_y__ = int(pixels_per_degree_y)
        self.__height__ = framebuffer_size[1]

        self.__reference_angles__ = range(
            -degrees_of_pitch,
            degrees_of_pitch + 1,
            10)
        self.__pitch_elements__ = {reference_angle: self.__generate_rotated_reference_angle__(reference_angle)
                                   for reference_angle in self.__reference_angles__}

    def __render_reference_line__(
        self,
        framebuffer,
        line_info,
        roll: float
    ):
        """
        Renders a single line of the AH ladder.

        Arguments:
            framebuffer {Surface} -- The target framebuffer to draw to.
            line_info {triplet} -- The line coords, center, and angle.
            rot_text {function} -- The function to rotate the text.
            roll {float} -- How much the plane is rolled.
        """

        line_coords, line_center, reference_angle = line_info
        pygame.draw.lines(
            framebuffer,
            colors.GREEN,
            False,
            line_coords,
            self.__line_width__)

        text, half_size = self.__pitch_elements__[reference_angle]
        roll = int(roll)
        # Since we will start with a limited number of pre-cached
        # pre-rotated textures (to improve boot time),
        # add any missing rotated textures using the upright
        # as the base.
        if roll not in text:
            rotated_surface = pygame.transform.rotate(text[0], roll)
            self.__pitch_elements__[reference_angle][0][roll] = rotated_surface
            text[roll] = rotated_surface

        text = text[roll]
        half_x, half_y = half_size
        center_x, center_y = line_center

        framebuffer.blit(text, (center_x - half_x, center_y - half_y))

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Renders the artificial horizon to the framebuffer

        Arguments:
            framebuffer {Surface} -- Target framebuffer to draw to.
            orientation {orientation} -- The airplane's orientation (roll & pitch)
        """

        # Creating aliases to the functions saves time...
        pitch = orientation.pitch
        roll = orientation.roll

        # Calculating the coordinates ahead of time...
        lines_centers_and_angles = [self.__get_line_coords__(
            pitch, roll, reference_angle) for reference_angle in self.__reference_angles__]
        # ... only to use filter to throw them out saves time.
        # This allows for the cores to be used and removes the conditionals
        # from the actual render function.
        lines_centers_and_angles = list(filter(
            lambda center:
            center[1][1] >= 0 and center[1][1] <= self.__height__, lines_centers_and_angles))

        [self.__render_reference_line__(framebuffer, line_info, roll)
            for line_info in lines_centers_and_angles]

    def __get_line_coords__(
        self,
        pitch: float,
        roll: float,
        reference_angle: int
    ):
        """
        Get the coordinate for the lines for a given pitch and roll.

        Arguments:
            pitch {float} -- The pitch of the plane.
            roll {float} -- The roll of the plane.
            reference_angle {int} -- The pitch angle to be marked on the AH.

        Returns:
            [tuple] -- An array[4] of the X/Y line coords.
        """

        length = self.__long_line_width__ if reference_angle == 0 else self.__short_line_width__

        roll_int = int(roll)

        ahrs_center_x, ahrs_center_y = self.__center__
        pitch_offset = self.__pixels_per_degree_y__ * \
            (-pitch + reference_angle)

        roll_delta = 90 - roll_int

        center_x = ahrs_center_x - \
            (pitch_offset * COS_RADIANS_BY_DEGREES[roll_delta]) + 0.5
        center_y = ahrs_center_y - \
            (pitch_offset * SIN_RADIANS_BY_DEGREES[roll_delta]) + 0.5

        center_x = int(center_x)
        center_y = int(center_y)

        x_len = int(length * COS_RADIANS_BY_DEGREES[roll_int] + 0.5)
        y_len = int(length * SIN_RADIANS_BY_DEGREES[roll_int] + 0.5)

        half_x_len = x_len >> 1
        half_y_len = y_len >> 1

        start_x = center_x - half_x_len
        end_x = center_x + half_x_len
        start_y = center_y + half_y_len
        end_y = center_y - half_y_len

        return [[start_x, start_y], [end_x, end_y]], (center_x, center_y), reference_angle


if __name__ == '__main__':
    run_ahrs_hud_element(ArtificialHorizon)
