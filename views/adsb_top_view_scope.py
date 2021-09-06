"""
View element for a "radar scope" that looks from the top downwards.
"""

import math
from typing import Tuple

import pygame
from common_utils import fast_math, geo_math, units
from common_utils.task_timer import TaskProfiler
from configuration import configuration
from core_services import breadcrumbs, zoom_tracker
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors, drawing

from views.adsb_element import AdsbElement
from views.hud_elements import apply_declination


class AdsbTopViewScope(AdsbElement):
    """
    A view element for the HUD that draws a radar style scope
    showing where traffic is relative to our current position.
    """

    # Arranged in (range, step_range)
    # So:
    # (1, 0) is 1 unit in range, no steps.
    # (5, 1) is 5 units in range, 1 unit steps
    # (20, 5) is 20 units in range, 5 unit steps

    ROTATION_PHASE_SHIFT = 90
    TRAFFIC_PHASE_SHIFT = -90
    TEXT_PHASE_SHIFT = 180

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size,
            reduced_visuals)

        self.__draw_identifiers__ = True

        self.__adjustment__ = 0.0

        # Make the center of the scope towards the bottome of the screen
        # such that we can see aircraft sneeking up behind us, but not so much
        # that we loose to much fidelity in front of us.
        self.__scope_center__ = [
            self.__center_x__,
            self.__center_y__ + int(self.__center_y__ >> 1)]

        size = self.__framebuffer_size__[1] * 0.04
        half_size = int((size / 2.0) + 0.5)
        quarter_size = int((size / 4.0) + 0.5)
        self.__no_direction_target_size__ = quarter_size

        # 1 - Come up with the 0,0 based line coordinates
        self.__target_indicator__ = [
            [-quarter_size, half_size],
            [0, -half_size],
            [quarter_size, half_size]
        ]

    def __get_traffic_indicator__(
        self,
        indicator_position: list,
        our_heading: float,
        traffic_heading: float
    ) -> list:
        """Generates the coordinates for a reticle indicating
        traffic is above use.

        Arguments:
            center_x {int} -- Center X screen position
            center_y {int} -- Center Y screen position
            scale {float} -- The scale of the reticle relative to the screen.
        """

        # 2 - determine the angle of rotation compared to our "up"
        rotation = 360.0 - our_heading
        rotation = rotation + traffic_heading
        rotation_degrees = int(
            fast_math.wrap_degrees(
                rotation + self.__adjustment__))

        # 3 - Rotate the zero-based points
        radians = math.radians(rotation_degrees)
        rotation_sin = math.sin(radians)
        rotation_cos = math.cos(radians)
        rotated_points = [
            [point[0] * rotation_cos - point[1] * rotation_sin,
             point[0] * rotation_sin + point[1] * rotation_cos] for point in self.__target_indicator__]

        # 4 - Translate to the bug center point
        return [[point[0] + indicator_position[0], point[1] + indicator_position[1]] for point in rotated_points]

    def __get_pixel_distance__(
        self,
        distance_in_user_units: float,
        scope_range: float
    ) -> int:
        max_pixel_distance = self.__scope_center__[1] - self.__top_border__

        if distance_in_user_units > scope_range:
            return max_pixel_distance

        proportion = distance_in_user_units / scope_range
        return int(max_pixel_distance * proportion)

    def __get_screen_projection_from_center__(
        self,
        angle_degrees: float,
        distance_pixels: float
    ) -> Tuple[int, int]:
        """
        Given an angle (0 is straight up, 180 is straight down), and a distance
        returns a x,y coordinate that locates the point FROM THE CENTER of the screen.

        Any angle with a distance of zero will be the center of the screen.
        An angle of 0 with a distance 1/2 screen vertical resolution will be at the top edge, between the left and right.
        An angle of 90 with a distance 1/2 screen horizontal resolution will be at the right edge, between the top and bottom.
        An angle of 180 with a distance 1/2 screen vertical resolution will be at the bottom edge, between the left and right.
        An angle of 270 with a distance 1/2 screen horizontal resolution will be at the left edge, between the top and bottom.

        Args:
            angle_degrees (float): The angle [0-359] relative to the top, center.
            distance_pixels (float): The number of pixels away from the center the point should be generated.

        Returns:
            (int, int): The x,y coordinates in screen space.
        """
        radians = math.radians(angle_degrees)
        reticle_x = math.cos(radians)
        reticle_y = math.sin(radians)
        screen_x = int((reticle_x * distance_pixels) + self.__scope_center__[0])
        screen_y = int((reticle_y * distance_pixels) + self.__scope_center__[1])

        return (screen_x, screen_y)

    def __render_on_screen_target__(
        self,
        framebuffer,
        orientation: AhrsData,
        traffic: Traffic,
        scope_range: float,
        first_ring_pixel_distance: int
    ):
        """
        Draws a single reticle on the screen.

        Arguments:
            framebuffer {pygame.Surface} -- Render target
            orientation {Orientation} -- The orientation of the plane.
            traffic {Traffic} -- The traffic to draw the reticle for.
            first_ring_pixel_distance {int} -- The distance (in pixels) from the ownship to the first scope ring. Used for clutter control.
        """

        # TODO - Make a pass to determine which targets
        # AND text top draw. Save both to lists.
        # THEN draw the text first, finally
        # drawing the targets over top.

        # TODO - Move the text to below the target indicator

        # TODO - Consider tail numbers to the side, with lines
        # that connect the number to the target.

        (is_within_threshold, display_distance) = zoom_tracker.INSTANCE.is_in_inner_range(traffic.distance)

        if not is_within_threshold:
            return

        pixels_from_center = self.__get_pixel_distance__(
            display_distance,
            scope_range)

        delta_angle = orientation.get_onscreen_gps_heading()
        delta_angle = traffic.bearing - delta_angle
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = AdsbTopViewScope.TRAFFIC_PHASE_SHIFT + delta_angle
        delta_angle = fast_math.wrap_degrees(delta_angle)

        # Find where to draw the reticle....
        screen_x, screen_y = self.__get_screen_projection_from_center__(
            delta_angle,
            pixels_from_center)

        if screen_x < 0 or screen_x > self.__width__:
            return

        if screen_y < 0 or screen_y > self.__height__:
            return

        target_color = colors.BLUE if traffic.is_on_ground() else colors.RED

        if traffic.track is not None:
            points = self.__get_traffic_indicator__(
                [screen_x, screen_y],
                orientation.get_onscreen_gps_heading(),
                traffic.track)
            drawing.renderer.polygon(framebuffer, target_color, points, not self.__reduced_visuals__)
        else:
            drawing.renderer.filled_circle(
                framebuffer,
                target_color,
                [screen_x, screen_y],
                self.__no_direction_target_size__,
                not self.__reduced_visuals__)

        # Do not draw identifier text for any targets further than
        # the first scope ring.
        if pixels_from_center > first_ring_pixel_distance:
            return

        if self.__draw_identifiers__:
            identifier = traffic.get_display_name()

            self.__render_centered_text__(
                framebuffer,
                identifier,
                [screen_x, screen_y + (self.__no_direction_target_size__ << 2)],
                colors.YELLOW,
                colors.BLACK,
                0.5,
                0,
                True)

            altitude_delta = int(traffic.altitude / 100.0)
            # No need to add a sign if it is negative. Math takes care of that for us.
            delta_sign = ''
            if altitude_delta > 0:
                delta_sign = '+'
            altitude_text = "{0}{1}".format(delta_sign, altitude_delta)

            self.__render_centered_text__(
                framebuffer,
                altitude_text,
                [screen_x, screen_y + self.__font_half_height__ + (self.__no_direction_target_size__ << 2)],
                colors.YELLOW,
                colors.BLACK,
                0.5,
                0,
                True)

    def __render_ownship__(
        self,
        framebuffer: pygame.Surface
    ):
        """
        Draws the graphic for an aircraft, but always pointing straight up.
        This is to indicate our own aircraft, position, and heading
        which will always be straight up.

        Args:
            framebuffer {pygame.Surface} -- The render target.
        """
        points = self.__get_traffic_indicator__(
            self.__scope_center__,
            0,
            0)

        drawing.renderer.polygon(framebuffer, colors.GREEN, points, not self.__reduced_visuals__)

    def __render_breadcrumbs__(
        self,
        framebuffer: pygame.Surface,
        scope_range: Tuple[int, int],
        orientation: AhrsData
    ):
        max_distance = scope_range[0]
        breadcrumb_reports = breadcrumbs.INSTANCE.get_trail()
        breadcrumb_count = len(breadcrumb_reports)

        if orientation.position is None or orientation.position[0] is None or orientation.position[1] is None:
            return

        if breadcrumb_count < 2:
            return

        current_heading = orientation.get_onscreen_gps_heading()

        if current_heading is None or isinstance(current_heading, str):
            return

        previous_position = None

        for index in range(breadcrumb_count - 1):
            proportion = breadcrumb_reports[index + 1][1]

            # if we need to continue due to the line
            # being off the screen or otherwise
            # invalid, we need to make sure
            # to disqualify the previous position
            # so we do not get any wacky looking completions
            if proportion <= 0.0:
                previous_position = None
                continue

            distance_start = geo_math.get_distance(orientation.position, breadcrumb_reports[index][0])

            if distance_start > max_distance:
                previous_position = None
                continue

            bearing = geo_math.get_bearing(orientation.position, breadcrumb_reports[index][0])
            delta_angle = bearing - current_heading
            # We need to rotate by 270 to make sure that
            # the orientation is correct AND to correct the phase.
            delta_angle = AdsbTopViewScope.TRAFFIC_PHASE_SHIFT + delta_angle
            delta_angle = fast_math.wrap_degrees(delta_angle)

            pixel_distance = self.__get_pixel_distance__(distance_start, max_distance)

            color = [int(component * proportion) for component in colors.GREEN]
            screen_coords = self.__get_screen_projection_from_center__(
                delta_angle,
                pixel_distance)

            if previous_position is not None:
                drawing.renderer.segment(
                    framebuffer,
                    color,
                    previous_position,
                    screen_coords,
                    width=self.__line_width__)

            previous_position = screen_coords

        # Complete the loop
        if previous_position is not None:
            drawing.renderer.segment(
                framebuffer,
                colors.GREEN,
                previous_position,
                self.__scope_center__,
                width=self.__line_width__)

    def __draw_distance_rings__(
        self,
        framebuffer: pygame.Surface,
        scope_range: Tuple[int, int]
    ) -> int:
        """
        Draws rings that indicate how far out another aircraft is.
        Each ring represents 5 units. The spacing will always be
        the same no matter what the units are.

        Args:
            framebuffer {pygame.Surface} -- The render target.

        Returns:
            int: The distance (in pixels from the center to the first ring. Used for clutter control.)
        """

        max_distance = scope_range[0]
        step = scope_range[1]
        ring_distances = [max_distance]
        distance_units = configuration.CONFIGURATION.get_units()
        units_suffix = units.get_distance_unit_suffix(distance_units)
        ring_pixel_distances = []

        if step > 0:
            ring_distances = list(
                range(
                    step,
                    int(scope_range[0]),
                    step))
            # To make it inclusive to the actual final ring
            # since range() does not include the last item.
            ring_distances.append(max_distance)

        radians = math.radians(30)
        sin_text_placement = math.sin(radians)
        cos_text_placement = math.cos(radians)

        for distance in ring_distances:
            radius_pixels = self.__get_pixel_distance__(distance, max_distance)
            drawing.renderer.circle(
                framebuffer,
                colors.GREEN,
                self.__scope_center__,
                radius_pixels,
                self.__thin_line_width__,
                not self.__reduced_visuals__)  # AA circle costs a BUNCH on the Pi
            ring_pixel_distances.append(radius_pixels)

            text_x = self.__scope_center__[0] + int(sin_text_placement * radius_pixels)
            text_y = self.__scope_center__[1] - int(cos_text_placement * radius_pixels)

            self.__render_text_with_stacked_annotations__(
                framebuffer,
                [text_x, text_y],
                [[1.0, str(int(distance)), colors.GREEN], [0.5, units_suffix, colors.GREEN]])

        return ring_pixel_distances[0]

    def __draw_compass_text__(
        self,
        framebuffer: pygame.Surface,
        our_heading: int,
        heading_to_draw: int,
        scope_range: int
    ):
        delta_angle = heading_to_draw - our_heading
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = fast_math.wrap_degrees(
            AdsbTopViewScope.ROTATION_PHASE_SHIFT + delta_angle)
        pixels_from_center = self.__get_pixel_distance__(
            scope_range, scope_range)

        screen_x, screen_y = self.__get_screen_projection_from_center__(
            apply_declination(delta_angle),
            pixels_from_center)

        heading_text_rotation = -(heading_to_draw - our_heading)
        heading_mark_rotation = -heading_text_rotation + 180

        indicator_mark_ends = fast_math.rotate_points(
            [[0, int(self.__line_width__ * -5)]],
            [0, 0],
            apply_declination(heading_mark_rotation))

        indicator_mark_ends = fast_math.translate_points(
            indicator_mark_ends,
            [screen_x, screen_y])

        drawing.renderer.segment(
            framebuffer,
            colors.GREEN,
            [screen_x, screen_y],
            indicator_mark_ends[0],
            self.__line_width__,
            not self.__reduced_visuals__)

        display_text = int(fast_math.wrap_degrees(AdsbTopViewScope.TEXT_PHASE_SHIFT + heading_to_draw))
        draw_text = (display_text % 90) == 0

        if not draw_text:
            return

        if not self.__reduced_visuals__:
            self.__render_centered_text__(
                framebuffer,
                str(display_text),
                (screen_x, screen_y),
                colors.BLACK,
                None,
                1.3,
                0,
                True)

        self.__render_centered_text__(
            framebuffer,
            str(display_text),
            (screen_x, screen_y),
            colors.YELLOW,
            colors.BLACK,
            1.0,
            0,
            not self.__reduced_visuals__)

    def __draw_all_compass_headings__(
        self,
        framebuffer: pygame.Surface,
        orientation: AhrsData,
        scope_range: int
    ):
        """
        Draw the text for ALL compass headings. 0, 90, 180, and 270
        This will make it clear that the scope is drawn user relative
        instead of absolute.

        Args:
            framebuffer (pygame.Surface): [description]
            orientation (AhrsData): [description]
        """
        try:
            our_heading = int(orientation.get_onscreen_gps_heading())
        except:
            # Heading is not a string, which means
            # we do not have GPS lock
            return

        for heading_to_draw in range(0, 360, 45):
            self.__draw_compass_text__(
                framebuffer,
                our_heading,
                heading_to_draw,
                scope_range)

    def render(
        self,
        framebuffer: pygame.Surface,
        orientation: AhrsData
    ):
        """
        Renders all of the on-screen reticles  for nearby traffic.

        Arguments:
            framebuffer {pygame.Surface} -- The render target.
            orientation {Orientation} -- The orientation of the plane the HUD is in.
        """

        # TODO: Investigate altitiude delta text
        # TODO: Try listing identifiers on side with lines leading to the aircraft
        # TODO: MORE TESTING!!!

        with TaskProfiler('views.adsb_top_view_scope.AdsbTopViewScope.setup'):
            scope_range = zoom_tracker.INSTANCE.get_target_zoom()
            traffic_reports = HudDataCache.get_reliable_traffic()
            traffic_reports.sort(
                key=lambda traffic: traffic.distance,
                reverse=True)

        near_target_distance = zoom_tracker.INSTANCE.get_target_threshold_distance()

        with TaskProfiler('views.adsb_top_view_scope.AdsbTopViewScope.render_breadcrumbs'):
            self.__render_breadcrumbs__(
                framebuffer,
                scope_range,
                orientation)

        with TaskProfiler('views.adsb_top_view_scope.AdsbTopViewScope.render'):
            self.__render_ownship__(framebuffer)

            first_ring_pixel_radius = self.__draw_distance_rings__(
                framebuffer,
                scope_range)

            self.__draw_all_compass_headings__(
                framebuffer,
                orientation,
                near_target_distance)

            if not orientation.gps_online:
                return

            # pylint: disable=expression-not-assigned
            [self.__render_on_screen_target__(
                framebuffer,
                orientation,
                traffic,
                near_target_distance,
                first_ring_pixel_radius) for traffic in traffic_reports]


if __name__ == '__main__':
    from views.compass_and_heading_top_element import \
        CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements

    run_hud_elements([CompassAndHeadingTopElement, Groundspeed, AdsbTopViewScope])
