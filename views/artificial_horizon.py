"""
Module to display the artificial horizon.
"""

from common_utils import fast_math, task_timer
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

        self.__long_segment_length__ = int(self.__width__ * 0.4)
        self.__short_segment_length__ = int(self.__width__ * 0.2)
        self.__inner_blank_area_length__ = int((self.__short_segment_length__ / 2)
                                               * 1.5)
        self.__pixels_per_degree_y__ = int(pixels_per_degree_y)

        self.__reference_angles__ = range(
            -degrees_of_pitch,
            degrees_of_pitch + 1,
            10)

        self.__upper_cull__ = -self.__font_height__
        self.__lower_cull__ = self.__height__ + self.__font_height__

    def __render_horizon_reference__(
        self,
        framebuffer,
        segments_info,
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

        segments, (center_x, center_y), reference_angle = segments_info

        for segment in segments:
            drawing.segment(
                framebuffer,
                colors.GREEN,
                segment[0],
                segment[1],
                self.__line_width__)

        roll = int(roll)

        is_not_visible_y = (center_y < self.__upper_cull__) \
            or (center_y > self.__lower_cull__)

        if is_not_visible_y:
            return

        self.__render_centered_text__(
            framebuffer,
            str(reference_angle),
            [center_x, center_y],
            colors.BLACK,
            None,
            1.2,
            roll,
            True)

        self.__render_centered_text__(
            framebuffer,
            str(reference_angle),
            [center_x, center_y],
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

        segment_generation = task_timer.TaskProfiler(
            "views.artificial_horizon.ArtificialHorizon.segment_generation")
        segment_generation.start()

        pitch_range = int(self.__center_x__ / self.__pixels_per_degree_y__)
        smallest_pitch = (orientation.pitch - pitch_range)
        largest_pitch = (orientation.pitch + pitch_range)

        angles_to_render = list(filter(
            lambda pitch: pitch < largest_pitch and pitch > smallest_pitch, self.__reference_angles__))

        # Calculating the coordinates ahead of time...
        segments_centers_and_angles = [self.__get_segment__(
            orientation.pitch,
            orientation.roll,
            reference_angle) for reference_angle in angles_to_render]
        segment_generation.stop()

        segment_render = task_timer.TaskProfiler(
            "views.artificial_horizon.ArtificialHorizon.segment_render")
        segment_render.start()
        # pylint: disable=expression-not-assigned
        [self.__render_horizon_reference__(
            framebuffer,
            segments,
            orientation.roll) for segments in segments_centers_and_angles]
        segment_render.stop()

    def __get_segment_endpoints__(
        self,
        length: int,
        pitch_offset: float,
        roll: float
    ) -> list:
        roll_delta = 90 - roll

        center_x = self.__center_x__ - \
            (pitch_offset * fast_math.cos(roll_delta)) + 0.5
        center_y = self.__center_y__ - \
            (pitch_offset * fast_math.sin(roll_delta)) + 0.5

        x_len = length * fast_math.cos(roll) + 0.5
        y_len = length * fast_math.sin(roll) + 0.5

        half_x_len = x_len / 2.0
        half_y_len = y_len / 2.0

        start_x = int(center_x - half_x_len)
        end_x = int(center_x + half_x_len)
        start_y = int(center_y + half_y_len)
        end_y = int(center_y - half_y_len)

        return [[start_x, start_y], [end_x, end_y]], (center_x, center_y)

    def __get_segment__(
        self,
        pitch: int,
        roll: int,
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

        length = self.__long_segment_length__ if reference_angle == 0 else self.__short_segment_length__
        pitch_offset = self.__pixels_per_degree_y__ * \
            (-pitch + reference_angle)

        outter_endpoints, center = self.__get_segment_endpoints__(
            length,
            pitch_offset,
            roll)

        inner_endpoints, _ = self.__get_segment_endpoints__(
            self.__inner_blank_area_length__,
            pitch_offset,
            roll)

        left_segment = [outter_endpoints[0], inner_endpoints[0]]
        right_segment = [outter_endpoints[1], inner_endpoints[1]]

        return [left_segment, right_segment], center, reference_angle


if __name__ == '__main__':
    run_ahrs_hud_element(ArtificialHorizon)
