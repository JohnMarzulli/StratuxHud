"""
View element for a "radar scope" that looks from the top downwards.
"""

import math
from datetime import datetime
from numbers import Number
from typing import Tuple

import pygame
from common_utils import fast_math, local_debug, units
from common_utils.fast_math import interpolatef
from common_utils.task_timer import TaskProfiler
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors, drawing

from views.adsb_element import AdsbElement


class ZoomTracker:
    """
    Tracks what our current zoom is and should be.
    Handles gracefully transitioning the desired
    zoom distance, while providing flapping prevention.
    """

    SECONDS_FOR_ZOOM = 3
    MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE = SECONDS_FOR_ZOOM * 5

    def __init__(
        self,
        starting_zoom: Tuple[int, int]
    ) -> None:
        super().__init__()

        self.__last_changed__ = datetime.utcnow()
        self.__last_zoom__ = starting_zoom
        self.__target_zoom__ = starting_zoom

    def set_target_zoom(
        self,
        new_target_zoom: Tuple[int, int]
    ):
        """
        Sets the desired target zoom distance.

        If a zoom target has been set too recently
        then the request is ignored. (Anti-flapping)

        Args:
            new_target_zoom (Tuple[int, int]): The total distance of the zoom and distance between rings.
        """

        if new_target_zoom is None:
            return

        if new_target_zoom[0] == self.__target_zoom__[0]:
            return

        delta_since_last_change = (datetime.utcnow() - self.__last_changed__).total_seconds()

        if delta_since_last_change < ZoomTracker.MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE:
            return

        print("Old target zoom={}".format(self.__target_zoom__))
        print("Setting new target zoom={}".format(new_target_zoom))

        self.__last_zoom__ = self.__target_zoom__
        self.__last_changed__ = datetime.utcnow()
        self.__target_zoom__ = new_target_zoom

    def get_target_zoom(
        self
    ) -> Tuple[Number, int]:
        """
        Get what our ideal, current zoom is.

        Returns a tuple that is the ideal distance
        AND the distance between rings.

        Returns:
            [Number, int]: The range and step of the scope rings
        """
        delta_since_last_change = (datetime.utcnow() - self.__last_changed__).total_seconds()

        proportion_into_zoom = delta_since_last_change / ZoomTracker.SECONDS_FOR_ZOOM

        if proportion_into_zoom >= 1.0:
            return self.__target_zoom__

        computed_range = interpolatef(
            self.__last_zoom__[0],
            self.__target_zoom__[0],
            proportion_into_zoom)

        # Determine the stepping to use based on
        # stepping of the rings. We want to always
        # use the largest stepping.
        #
        # We choose this way so the whole process has visual consistency
        # and does not startle the aviator.
        previous_zoom_stepping = self.__last_zoom__[1]
        new_zoom_stepping = self.__target_zoom__[1]

        target_zoom_step = max(new_zoom_stepping, previous_zoom_stepping)

        return [computed_range, target_zoom_step]


DEFAULT_SCOPE_RANGE = (10, 5)

SCOPE_RANGES = [
    (1, 0),
    (2, 1),
    (5, 1),
    (10, 5),
    (15, 5),
    (20, 5),
    (50, 10)]


def __get_maximum_scope_range__() -> Tuple[int, int]:
    """
    Get the maximum

    Returns:
        (int, int): Tuple of the maximum distance for the scope, and the distance between each ring.
    """
    return SCOPE_RANGES[-1]


__DISTANCE_PREDICTION_SCALER__ = 12


def __get_ideal_scope_range__(
    groundspeed: float
) -> Tuple[int, int]:
    """
    Given a ground speed, figure out how far the scope should be.
    This is done by figuring out how far you will be in 10 minutes

    Args:
        groundspeed (float): The speed to calculate the ideal scope range from. This is in final units (so MPH, KPH, KNOTS)

    Returns:
        (int, int): The maximum distance the scope will cover and the distance between each ring.

    >>> __get_ideal_scope_range__(0.0)
    (1, 0)
    >>> __get_ideal_scope_range__(0)
    (1, 0)
    >>> __get_ideal_scope_range__(-1 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(-1.0 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(0.5 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(1 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(1.0 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(1.1 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(1.5 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(1.9 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(2.0 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(2.1 * __DISTANCE_PREDICTION_SCALER__)
    (5, 1)
    >>> __get_ideal_scope_range__(5 * __DISTANCE_PREDICTION_SCALER__)
    (5, 1)
    >>> __get_ideal_scope_range__(9.9 * __DISTANCE_PREDICTION_SCALER__)
    (10, 5)
    >>> __get_ideal_scope_range__(10 * __DISTANCE_PREDICTION_SCALER__)
    (10, 5)
    >>> __get_ideal_scope_range__(14.9 * __DISTANCE_PREDICTION_SCALER__)
    (15, 5)
    >>> __get_ideal_scope_range__(15 * __DISTANCE_PREDICTION_SCALER__)
    (15, 5)
    >>> __get_ideal_scope_range__(19.9 * __DISTANCE_PREDICTION_SCALER__)
    (20, 5)
    >>> __get_ideal_scope_range__(20 * __DISTANCE_PREDICTION_SCALER__)
    (20, 5)
    >>> __get_ideal_scope_range__(20.1 * __DISTANCE_PREDICTION_SCALER__)
    (50, 10)
    >>> __get_ideal_scope_range__(50 * __DISTANCE_PREDICTION_SCALER__)
    (50, 10)
    >>> __get_ideal_scope_range__(100 * __DISTANCE_PREDICTION_SCALER__)
    (50, 10)
    """

    predicted_travel_distance = math.fabs(groundspeed) / __DISTANCE_PREDICTION_SCALER__

    # The idea is to return the first range in the set
    # that is further than you will fly in 10 minutes.
    for possible_range in SCOPE_RANGES:
        range_distance = possible_range[0]
        if range_distance >= predicted_travel_distance:
            return possible_range

    return __get_maximum_scope_range__()


def __get_groundspeed__(
    orientation: AhrsData
) -> float:
    is_valid_groundspeed = orientation.groundspeed is not None and isinstance(orientation.groundspeed, Number)
    is_valid_airspeed = orientation.airspeed is not None and isinstance(orientation.airspeed, Number)

    airspeed = units.get_converted_units(
        configuration.CONFIGURATION.get_units(),
        orientation.airspeed * units.feet_to_nm) if is_valid_airspeed else 0.0

    groundspeed = units.get_converted_units(
        configuration.CONFIGURATION.get_units(),
        orientation.groundspeed * units.yards_to_nm) if is_valid_groundspeed else 0

    if local_debug.is_debug() and is_valid_airspeed:
        return airspeed

    return groundspeed


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

    ROTATION_PHASE_SHIFT = 270

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

        self.__zoom_tracker__ = ZoomTracker(DEFAULT_SCOPE_RANGE)

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
        translated_points = [
            [point[0] + indicator_position[0],
             point[1] + indicator_position[1]] for point in rotated_points]

        return translated_points

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

        display_distance = units.get_converted_units(
            configuration.CONFIGURATION.get_units(),
            traffic.distance)

        if display_distance > scope_range:
            return

        pixels_from_center = self.__get_pixel_distance__(
            display_distance,
            scope_range)

        delta_angle = orientation.get_onscreen_projection_heading()
        delta_angle = traffic.bearing - delta_angle
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = fast_math.wrap_degrees(
            AdsbTopViewScope.ROTATION_PHASE_SHIFT + delta_angle)

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
                orientation.get_onscreen_projection_heading(),
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
            delta_angle,
            pixels_from_center)

        heading_text_rotation = -(heading_to_draw - our_heading)

        indicator_mark_ends = fast_math.rotate_points(
            [[0, int(self.__line_width__ * -5)]],
            [0, 0],
            -heading_text_rotation + 180)

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

        draw_text = (heading_to_draw % 90) == 0

        if not draw_text:
            return

        if not self.__reduced_visuals__:
            self.__render_centered_text__(
                framebuffer,
                str(heading_to_draw),
                (screen_x, screen_y),
                colors.BLACK,
                None,
                1.3,
                heading_text_rotation,
                True)

        self.__render_centered_text__(
            framebuffer,
            str(heading_to_draw),
            (screen_x, screen_y),
            colors.YELLOW,
            colors.BLACK,
            1.0,
            heading_text_rotation,
            True)

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
            our_heading = int(orientation.get_onscreen_projection_heading())
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

    def __get_scope_zoom__(
        self,
        orientation: AhrsData
    ) -> Tuple[Number, float]:
        groundspeed = __get_groundspeed__(orientation)

        ideal_range = __get_ideal_scope_range__(groundspeed)

        # TODO - Make sure that the zoom rings are properly scoping in and out
        self.__zoom_tracker__.set_target_zoom(ideal_range)

        return self.__zoom_tracker__.get_target_zoom()

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
            scope_range = self.__get_scope_zoom__(orientation)
            traffic_reports = HudDataCache.get_reliable_traffic()
            traffic_reports.sort(
                key=lambda traffic: traffic.distance,
                reverse=True)

        with TaskProfiler('views.adsb_top_view_scope.AdsbTopViewScope.render'):
            self.__render_ownship__(framebuffer)

            first_ring_pixel_radius = self.__draw_distance_rings__(
                framebuffer,
                scope_range)

            self.__draw_all_compass_headings__(
                framebuffer,
                orientation,
                scope_range[0])

            # pylint: disable=expression-not-assigned
            [self.__render_on_screen_target__(
                framebuffer,
                orientation,
                traffic,
                scope_range[0],
                first_ring_pixel_radius) for traffic in traffic_reports]


if __name__ == '__main__':
    import doctest

    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements

    print("Starting tests.")

    doctest.testmod()

    print("Tests finished")

    run_hud_elements([Groundspeed, AdsbTopViewScope])
