"""
Indicates to the pilot the current roll angle.
"""

from common_utils import local_debug
from common_utils.fast_math import cos, rotate_points, sin, translate_points
from data_sources.ahrs_data import AhrsData
from rendering import colors, drawing

from views.ahrs_element import AhrsElement


class RollIndicator(AhrsElement):
    """
    Element to indicate the current roll from AHRS.
    """

    # pylint:disable=unused-argument
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        self.__text_y_pos__ = self.__center_y__ - self.__font_half_height__
        self.arc_radius = int(self.__height__ * .4)
        self.__indicator_arc_center__ = [
            self.__center__[0],
            self.__center__[1]]
        self.__indicator_arc__ = self.__get_points_on_arc__(range(-60, 61, 5))

        self.__zero_angle_triangle__ = self.__get_upper_angle_reference_shape__()
        self.__current_angle_triangle__ = self.__get_current_angle_triangle_shape__()
        self.__current_angle_box__ = self.__get_current_angle_box_shape__()
        self.__arc_width__ = int(self.__line_width__ * 1.5)
        self.__roll_angle_marks__ = self.__get_major_roll_indicator_marks__()

    def __get_point_on_arc__(
        self,
        radius: int,
        start_angle: int,
    ) -> list:
        """
        Given an angle and a radius, calculate the x,y for the point on a circle.
        Assumes a center of 0,0

        Args:
            radius (int): The radius of the circle/arc
            start_angle (int): The angle to generate the point for.

        Returns:
            list: The x,y of the point on the circle.
        """
        point = [radius * sin(start_angle), radius * cos(start_angle)]

        return point

    def __get_points_on_arc__(
        self,
        angles: list
    ) -> list:
        """
        Given a list of angles, generate the points for them
        on the roll indicator arc.

        Args:
            angles (list): The list of points to get the circle points for.

        Returns:
            list: The list of points on the indicator arc.
        """
        segments = [self.__get_point_on_arc__(
            self.arc_radius,
            start_angle - 180) for start_angle in angles]

        return translate_points(segments, self.__indicator_arc_center__)

    def __get_angle_mark_points__(
        self
    ) -> dict:
        """
        Get the list of line segments that define the angle indication marks.

        Returns:
            dict: A dictionary, keyed by angle, of where the indicator marks start.
        """
        angles = [-60, -45, -30, 0, 30, 45, 60]
        mark_start_points = self.__get_points_on_arc__(angles)

        angle_and_start_points = {}
        index = 0

        for angle in angles:
            angle_and_start_points[angle] = mark_start_points[index]
            index += 1

        return angle_and_start_points

    def __get_arc_center__(
        self
    ) -> list:
        """
        Get the top-center point of the indicator arc (0 degrees)

        Returns:
            list: The x,y of the arc center/nuetral
        """
        return self.__get_points_on_arc__([0])[0]

    def __get_upper_angle_reference_shape__(
        self
    ) -> list:
        """
        Generates the triangle shape that indicates the zero-roll/level
        position on the indicator arc. It is intended to be shown
        as a triangle, with the point facing down.
        The position is to be with the point touching the arc,
        with all points above the arc.

        Returns:
            list: A list of points that describe a closed shape.
        """
        zero_angle_triangle_size = int(self.__width__ * 0.01)
        bottom_point = self.__get_arc_center__()[1]

        bottom = bottom_point - self.__thick_line_width__
        left = self.__center_x__ - zero_angle_triangle_size
        right = self.__center_x__ + zero_angle_triangle_size
        top = bottom - int(self.arc_radius / 8) + self.__thick_line_width__

        return [[self.__center_x__, bottom], [left, top], [right, top]]

    def __get_current_angle_triangle_shape__(
        self
    ) -> list:
        """
        Generates the triangle shape that indicates the current
        roll along the indicator arc.
        It is intended to be shown as a triangle, with the point facing up.
        The position is to be with the point touching the arc.
        All points would be below the arc.

        Returns:
            list: A list of points that describe a closed shape.
        """
        zero_angle_triangle_size = int(self.__width__ * 0.01)

        top_point = self.__get_arc_center__()[1]
        top = top_point + self.__thick_line_width__ + 1

        bottom = top + (zero_angle_triangle_size << 1) + 1
        left = self.__center_x__ - zero_angle_triangle_size
        right = self.__center_x__ + zero_angle_triangle_size

        return [[self.__center_x__, top], [left, bottom], [right, bottom]]

    def __get_current_angle_box_shape__(
        self
    ) -> list:
        """
        Generates an "underline" box for the current angle indicator.
        The positions is intended to be below the flat base
        of the indicator triangle.

        Returns:
            list: A list of points that describe a closed shape.
        """
        zero_angle_triangle_size = int(self.__width__ * 0.01)

        top_point = self.__get_arc_center__()[1]
        top = top_point + self.__thin_line_width__ + 1

        top = top + (zero_angle_triangle_size << 1) + \
            int(self.__line_width__ * 1.5)
        bottom = top + self.__line_width__
        left = self.__center_x__ - zero_angle_triangle_size
        right = self.__center_x__ + zero_angle_triangle_size

        return [[left, top], [right, top], [right, bottom], [left, bottom]]

    def __get_major_roll_indicator_marks__(
        self
    ) -> list:
        """
        Generates a list of line segments.
        Each line segment describes an indicator mark for the
        roll indicator arc.

        The position of the marks is intended to start "on" the arc
        and then procede to the top of the screen.
        Each mark will be angled to match the roll angle.
        For example, the 60deg mark is angled 60 away from verticle.

        Returns:
            list: A list containing line segments. Each segment is two points.
        """

        # What needs to happen:
        # Build a dictionary that is keyed by angle.
        # The value is the roll indicator line
        # The line segment is calculated by:
        # - Find the point on the circle for the roll
        # - Define a line that starts at 0,0, then goes up the determined distance
        # - Rotate the segment by the rotation
        # - Translate the segment by the point on the circle
        angles_and_start_points = self.__get_angle_mark_points__()

        roll_angle_marks = []

        major_mark_length = int(self.arc_radius / 8)
        minor_mark_length = major_mark_length >> 1

        for roll_angle in list(angles_and_start_points.keys()):
            mark_length = major_mark_length if roll_angle % 10 == 0 else minor_mark_length
            angle_mark_start = angles_and_start_points[roll_angle]
            angle_mark_end = [0, mark_length]

            angle_mark_end = rotate_points(
                [angle_mark_end],
                [0, 0],
                roll_angle)[0]
            angle_mark_end[0] = angle_mark_end[0] + angle_mark_start[0]
            angle_mark_end[1] = angle_mark_start[1] - angle_mark_end[1]

            roll_angle_marks.append([angle_mark_start, angle_mark_end])

        return roll_angle_marks

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        # Use jagged lines at the moment on the
        # Pi given the cost of anti-aliasing
        is_antialiased = not local_debug.IS_PI

        drawing.segments(
            framebuffer,
            colors.WHITE,
            False,
            self.__indicator_arc__,
            self.__arc_width__,
            is_antialiased)

        # Draw the important angle/roll step marks
        for segment_start, segment_end in self.__roll_angle_marks__:
            drawing.segment(
                framebuffer,
                colors.WHITE,
                segment_start,
                segment_end,
                self.__line_width__,
                True)

            if not local_debug.IS_PI:
                drawing.filled_circle(
                    framebuffer,
                    colors.WHITE,
                    segment_start,
                    self.__thin_line_width__)

        # Draws the current roll
        drawing.polygon(
            framebuffer,
            colors.WHITE,
            rotate_points(
                self.__zero_angle_triangle__,
                self.__indicator_arc_center__,
                -orientation.roll),
            is_antialiased)

        drawing.polygon(
            framebuffer,
            colors.WHITE,
            rotate_points(
                self.__current_angle_triangle__,
                self.__indicator_arc_center__,
                -orientation.roll),
            is_antialiased)

        drawing.polygon(
            framebuffer,
            colors.WHITE,
            rotate_points(
                self.__current_angle_box__,
                self.__indicator_arc_center__,
                -orientation.roll),
            is_antialiased)


if __name__ == '__main__':
    from views.hud_elements import run_hud_element
    run_hud_element(RollIndicator, False)
