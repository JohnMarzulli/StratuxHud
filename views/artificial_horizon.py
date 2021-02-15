"""
Module to display the artificial horizon.
"""

from common_utils import fast_math
from data_sources.ahrs_data import AhrsData
from rendering import drawing

from views.ahrs_element import AhrsElement
from views.hud_elements import colors, run_ahrs_hud_element


class ArtificialHorizon(AhrsElement):
    """
    Element to display the artificial horizon.
    """

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
        drawing.segments(
            framebuffer,
            colors.GREEN,
            False,
            line_coords,
            self.__line_width__)

        roll = int(roll)

        self.__render_centered_text__(
            framebuffer,
            str(reference_angle),
            (line_center[0], line_center[1]),
            colors.WHITE,
            None,
            1.0,
            roll,
            True)

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

        # pylint: disable=expression-not-assigned
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
            (pitch_offset * fast_math.cos(roll_delta)) + 0.5
        center_y = ahrs_center_y - \
            (pitch_offset * fast_math.sin(roll_delta)) + 0.5

        center_x = int(center_x)
        center_y = int(center_y)

        x_len = int(length * fast_math.cos(roll_int) + 0.5)
        y_len = int(length * fast_math.sin(roll_int) + 0.5)

        half_x_len = x_len >> 1
        half_y_len = y_len >> 1

        start_x = center_x - half_x_len
        end_x = center_x + half_x_len
        start_y = center_y + half_y_len
        end_y = center_y - half_y_len

        return [[start_x, start_y], [end_x, end_y]], (center_x, center_y), reference_angle


if __name__ == '__main__':
    run_ahrs_hud_element(ArtificialHorizon)
