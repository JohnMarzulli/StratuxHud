import math
from typing import List

import pygame
from common_utils.fast_math import cos, rotate_points, sin, translate_points
from data_sources.ahrs_data import AhrsData
from rendering import colors

from views.ahrs_element import AhrsElement


class RollIndicatorText(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        self.__roll_elements__ = {}
        self.__text_y_pos__ = self.__center_y__ - self.__font_half_height__

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
        text_half_width = text_half_width >> 1
        framebuffer.blit(
            roll_texture,
            (self.__center_x__ - text_half_width, self.__text_y_pos__))


class RollIndicator(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        self.__text_y_pos__ = self.__center_y__ - self.__font_half_height__
        self.arc_radius = int(self.__width__ /3)
        self.__indicator_arc_center__ = [self.__center__[0], self.__center__[1] + (self.arc_radius >> 2)] # + (self.arc_radius >> 1)]
        self.__indicator_arc__ = self.__get_arc_line_segements__(self.__indicator_arc_center__)

        self.__zero_angle_triangle__ = self.__get_zero_angle_reference_shape__()
        self.__current_angle_triangle__ = self.__get_current_angle_triangle_shape__()
        self.__current_angle_box__ = self.__get_current_angle_box_shape__()
        self.__arc_width__ = int(self.__line_width__ * 1.5)
        self.__roll_angle_marks__ = self.__get_major_roll_indicator_marks__()

    def __get_point_on_arc__(
        self,
        radius: int,
        start_angle: int,
    ) -> list:
        point = [radius * sin(start_angle), radius * cos(start_angle)]

        return point
        

    def __get_arc_line_segements__(
        self,
        center: list
    ) -> list:
        segments = [self.__get_point_on_arc__(
            self.arc_radius, start_angle - 180) for start_angle in range(-60, 61, 5)]
        return translate_points(segments, center)
    
    def __get_angle_mark_points__(
        self,
        center: dict
    ) -> dict:
        angles = [-60, -30, 30, 60]
        segments = [self.__get_point_on_arc__(
            self.arc_radius,
            start_angle - 180) for start_angle in angles]
        translated_points = translate_points(segments, center)

        angle_and_start_points = {}
        index = 0

        for angle in angles:
            angle_and_start_points[angle] = translated_points[index]
            index += 1
        
        return angle_and_start_points
    
    def get_middle_index(
        self,
        point_list: list
    ) -> int:
        middle = float(len(point_list))/2
        if middle % 2 != 0:
            return int(middle - .5)
        else:
            return middle

    def __get_zero_angle_reference_shape__(
        self
    ) -> list:
        zero_angle_triangle_size = int(self.__width__ * 0.01)
        middle_index = self.get_middle_index(self.__indicator_arc__)
        bottom_point = self.__indicator_arc__[middle_index][1]

        bottom = bottom_point - (self.__line_width__ << 1) - 1
        left = self.__center_x__ - zero_angle_triangle_size
        right = self.__center_x__ + zero_angle_triangle_size
        top = bottom - (zero_angle_triangle_size << 1) - (self.__line_width__ >> 1) - 1

        return [[self.__center_x__, bottom], [left, top], [right, top]]

    def __get_current_angle_triangle_shape__(
        self
    ) -> list:
        zero_angle_triangle_size = int(self.__width__ * 0.015)

        middle_index = self.get_middle_index(self.__indicator_arc__)
        top_point = self.__indicator_arc__[middle_index][1]
        top = top_point + (self.__line_width__ << 1) + 1

        bottom = top + (zero_angle_triangle_size << 1) + 1
        left = self.__center_x__ - zero_angle_triangle_size
        right = self.__center_x__ + zero_angle_triangle_size

        return [[self.__center_x__, top], [left, bottom], [right, bottom]]

    def __get_current_angle_box_shape__(
        self
    ) -> list:
        zero_angle_triangle_size = int(self.__width__ * 0.015)

        middle_index = self.get_middle_index(self.__indicator_arc__)
        top_point = self.__indicator_arc__[middle_index][1]
        top = top_point + (self.__line_width__ << 1) + 1

        top = top + (zero_angle_triangle_size << 1) + int(self.__line_width__ * 1.5)
        bottom = top + self.__line_width__
        left = self.__center_x__ - zero_angle_triangle_size
        right = self.__center_x__ + zero_angle_triangle_size

        return [[left, top], [right, top], [right, bottom], [left, bottom]]
    
    def __get_major_roll_indicator_marks__(
        self
    ) -> list:
        # What needs to happen:
        # Build a dictionary that is keyed by angle.
        # The value is the roll indicator line
        # The line segment is calculated by:
        # - Find the point on the circle for the roll
        # - Define a line that starts at 0,0, then goes up the determined distance
        # - Rotate the segment by the rotation
        # - Translate the segment by the point on the circle
        angles_and_start_points = self.__get_angle_mark_points__(self.__indicator_arc_center__)

        roll_angle_marks = []

        for roll_angle in list(angles_and_start_points.keys()):
            angle_mark_start = angles_and_start_points[roll_angle]
            angle_mark_end = [0, int(self.arc_radius / 10)]

            angle_mark_end = rotate_points([angle_mark_end], [0,0], roll_angle)[0]
            angle_mark_end[0] = angle_mark_end[0] + angle_mark_start[0]
            angle_mark_end[1] = angle_mark_start[1] - angle_mark_end[1]

            roll_angle_marks.append([angle_mark_start, angle_mark_end])
        
        return roll_angle_marks

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        pygame.draw.lines(
            framebuffer,
            colors.WHITE,
            False,
            self.__indicator_arc__,
            self.__arc_width__)

        # Render the Zero line
        pygame.draw.polygon(
            framebuffer,
            colors.WHITE,
            self.__zero_angle_triangle__,
            0)  # Make filled

        # Draw the important angle/roll step marks
        for segment_start, segment_end in self.__roll_angle_marks__:
            pygame.draw.line(
                framebuffer,
                colors.WHITE,
                segment_start,
                segment_end,
                self.__line_width__)

        # Draws the current roll
        pygame.draw.polygon(
            framebuffer,
            colors.WHITE,
            rotate_points(
                self.__current_angle_triangle__,
                self.__indicator_arc_center__,
                orientation.roll),
            0)  # Make filled

        pygame.draw.polygon(
            framebuffer,
            colors.WHITE,
            rotate_points(
                self.__current_angle_box__,
                self.__indicator_arc_center__,
                orientation.roll),
            0)  # Make filled


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element
    run_ahrs_hud_element(RollIndicator, False)
