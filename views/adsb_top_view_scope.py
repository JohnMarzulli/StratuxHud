import math
from datetime import datetime
from numbers import Number

import pygame
from common_utils import local_debug, units
from common_utils.task_timer import TaskTimer
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from pygame import Surface
from rendering import colors

from views.adsb_element import AdsbElement
from views.hud_elements import wrap_angle


def clamp(
    minimum,
    value,
    maximum
):
    """
    Makes sure the given value (middle param) is always between the maximum and minimum.

    Arguments:
        minimum {number} -- The smallest the value can be (inclusive).
        value {number} -- The value to clamp.
        maximum {number} -- The largest the value can be (inclusive).

    Returns:
        number -- The value within the allowable range.
    """

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def interpolate(
    left_value,
    right_value,
    proportion
):
    """
    Finds the spot between the two values.

    Arguments:
        left_value {number} -- The value on the "left" that 0.0 would return.
        right_value {number} -- The value on the "right" that 1.0 would return.
        proportion {float} -- The proportion from the left to the right hand side.

    >>> interpolate(0, 255, 0.5)
    127
    >>> interpolate(10, 20, 0.5)
    15
    >>> interpolate(0, 255, 0.0)
    0
    >>> interpolate(0, 255, 0)
    0
    >>> interpolate(0, 255, 1)
    255
    >>> interpolate(0, 255, 1.5)
    255
    >>> interpolate(0, 255, -0.5)
    0
    >>> interpolate(0, 255, 0.1)
    25
    >>> interpolate(0, 255, 0.9)
    229
    >>> interpolate(255, 0, 0.5)
    127
    >>> interpolate(20, 10, 0.5)
    15
    >>> interpolate(255, 0, 0.0)
    255
    >>> interpolate(255, 0, 0)
    255
    >>> interpolate(255, 0, 1)
    0
    >>> interpolate(255, 0, 1.5)
    0
    >>> interpolate(255, 0, -0.5)
    255
    >>> interpolate(255, 0, 0.1)
    229
    >>> interpolate(255, 0, 0.9)
    25

    Returns:
        float -- The number that is the given amount between the left and right.
    """

    left_value = clamp(0.0, left_value, 255.0)
    right_value = clamp(0.0, right_value, 255.0)
    proportion = clamp(0.0, proportion, 1.0)

    return clamp(
        0,
        int(float(left_value) + (float(right_value -
                                       float(left_value)) * float(proportion))),
        255)


class ZoomTracker(object):
    SECONDS_FOR_ZOOM = 3
    MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE = SECONDS_FOR_ZOOM * 5

    def __init__(
        self,
        starting_zoom: (int,  int)
    ) -> None:
        super().__init__()

        self.__last_changed__ = datetime.utcnow()
        self.__last_zoom__ = starting_zoom
        self.__target_zoom__ = starting_zoom

    def set_target_zoom(
        self,
        new_target_zoom: (int, int)
    ):
        if new_target_zoom is None:
            return

        if new_target_zoom[0] == self.__target_zoom__[0]:
            return

        delta_since_last_change = (
            datetime.utcnow() - self.__last_changed__).total_seconds()

        if delta_since_last_change < ZoomTracker.MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE:
            return

        self.__last_zoom__ = self.__target_zoom__
        self.__last_changed__ = datetime.utcnow()
        self.__target_zoom__ = new_target_zoom

    def get_target_zoom(
        self
    ):
        delta_since_last_change = (
            datetime.utcnow() - self.__last_changed__).total_seconds()

        proportion_into_zoom = delta_since_last_change / ZoomTracker.SECONDS_FOR_ZOOM

        if proportion_into_zoom > 1.0:
            return self.__target_zoom__

        computed_range = interpolate(
            self.__last_zoom__[0],
            self.__target_zoom__[0],
            proportion_into_zoom)

        # Use the minor steps from the previous zoom
        # so the whole process has visual consistency
        # and does not startle the aviator.
        return [computed_range, self.__last_zoom__[1]]


class AdsbTopViewScope(AdsbElement):

    # Arranged in (range, step_range)
    # So:
    # (1, 0) is 1 unit in range, no steps.
    # (5, 1) is 5 units in range, 1 unit steps
    # (20, 5) is 20 units in range, 5 unit steps

    DEFAULT_SCOPE_RANGE = (10, 5)
    SCOPE_RANGES = [
        (1, 0),
        (2, 1),
        (5, 1),
        (10, 5),
        (15, 5),
        (20, 5),
        (50, 10)]
    ROTATION_PHASE_SHIFT = 270

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        AdsbElement.__init__(
            self,
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size)

        self.task_timer = TaskTimer('AdsbTopViewScope')
        self.rings_timer = TaskTimer('AdsbTopViewScopeRings')
        self.bugs_timer = TaskTimer('AdsbTopViewScopeBugs')
        self.range_timer = TaskTimer('AdsbTopViewScopeScopeRange')

        self.__top_border__ = int(self.__height__ * 0.05)
        self.__bottom_border__ = self.__height__ - self.__top_border__

        self.__draw_identifiers__ = True

        self.__adjustment__ = 0.0

        # Make the center of the scope towards the bottome of the screen
        # such that we can see aircraft sneeking up behind us, but not so much
        # that we loose to much fidelity in front of us.
        self.__scope_center__ = [self.__center__[0],
                                 self.__center__[1] + (self.__center__[1] >> 1)]

        self.__zoom_tracker__ = ZoomTracker(
            AdsbTopViewScope.DEFAULT_SCOPE_RANGE)

    def __get_maximum_scope_range__(
        self
    ) -> (int, int):
        """
        Get the maximum

        Returns:
            (int, int): Tuple of the maximum distance for the scope, and the distance between each ring.
        """
        return AdsbTopViewScope.SCOPE_RANGES[:1][0]

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

        # TODO: Make the scale varibale.
        size = self.__framebuffer_size__[1] * 0.04
        half_size = int((size / 2.0) + 0.5)
        quarter_size = int((size / 4.0) + 0.5)

        # 1 - Come up with the 0,0 based line coordinates
        target = [
            [-quarter_size, half_size],
            [0, -half_size],
            [quarter_size, half_size]
        ]

        # 2 - determine the angle of rotation compared to our "up"
        rotation = 360.0 - our_heading
        rotation = rotation + traffic_heading
        rotation = wrap_angle(rotation + self.__adjustment__)

        # 3 - Rotate the zero-based points
        rotation_radians = math.radians(rotation)
        rotation_sin = math.sin(rotation_radians)
        rotation_cos = math.cos(rotation_radians)
        rotated_points = [[point[0] * rotation_cos - point[1] * rotation_sin,
                           point[0] * rotation_sin + point[1] * rotation_cos] for point in target]

        # 4 - Translate to the bug center point
        translated_points = [(point[0] + indicator_position[0],
                              point[1] + indicator_position[1]) for point in rotated_points]

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
    ) -> (int, int):
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
        delta_angle_radians = math.radians(angle_degrees)
        reticle_x = math.cos(delta_angle_radians)
        reticle_y = math.sin(delta_angle_radians)
        screen_x = (reticle_x * distance_pixels) + self.__scope_center__[0]
        screen_y = (reticle_y * distance_pixels) + self.__scope_center__[1]

        return (int(screen_x), int(screen_y))

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
            framebuffer {Surface} -- Render target
            orientation {Orientation} -- The orientation of the plane.
            traffic {Traffic} -- The traffic to draw the reticle for.
            first_ring_pixel_distance {int} -- The distance (in pixels) from the ownship to the first scope ring. Used for clutter control.
        """

        display_distance = units.get_converted_units(
            configuration.CONFIGURATION.get_units(),
            traffic.distance)

        if display_distance > scope_range:
            return

        pixels_from_center = self.__get_pixel_distance__(
            display_distance,
            scope_range)

        delta_angle = orientation.get_heading()
        delta_angle = traffic.bearing - delta_angle
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = wrap_angle(
            AdsbTopViewScope.ROTATION_PHASE_SHIFT + delta_angle)

        # Find where to draw the reticle....
        screen_x, screen_y = self.__get_screen_projection_from_center__(
            delta_angle,
            pixels_from_center)

        if screen_x < 0 or screen_x > self.__width__:
            return

        if screen_y < 0 or screen_y > self.__height__:
            return

        target_color = colors.BLUE if traffic.is_on_ground() == True else colors.RED

        if traffic.track is not None:
            points = self.__get_traffic_indicator__(
                [screen_x, screen_y],
                orientation.get_heading(),
                traffic.track)
            pygame.draw.polygon(framebuffer, target_color, points)
        else:
            pygame.draw.circle(
                framebuffer,
                target_color,
                (screen_x, screen_y),
                4,
                4)

        # Do not draw identifier text for any targets further than
        # the first scope ring.
        if pixels_from_center > first_ring_pixel_distance:
            return

        if self.__draw_identifiers__:
            identifier = traffic.get_display_name()

            rendered_text, size = HudDataCache.get_cached_text_texture(
                identifier,
                self.__font__,
                colors.YELLOW,
                colors.BLACK,
                True,
                False)

            # Half size to reduce text clutter
            # rendered_text = pygame.transform.smoothscale(
            #     rendered_text,
            #     [size[0] >> 1, size[1] >> 1])

            framebuffer.blit(
                rendered_text,
                (screen_x, screen_y),
                special_flags=pygame.BLEND_RGBA_ADD)

    def __render_heading_text__(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Renders your current heading at the top of the scope.

        Args:
            framebuffer: The framebuffer to render to.
            orientation (AhrsData): Our current AHRS data.
        """
        rendered_text, size = HudDataCache.get_cached_text_texture(
            '{0:03d}'.format(orientation.get_heading()),
            self.__font__,
            colors.GREEN,
            colors.BLACK,
            True,
            False)

        half_width = size[0] >> 1
        text_height = size[1]
        border_size = text_height >> 3

        framebuffer.blit(
            rendered_text,
            ((self.__center__[0] - half_width), self.__top_border__),
            special_flags=pygame.BLEND_RGBA_ADD)

        left = self.__center__[0] - half_width - border_size
        right = self.__center__[0] + half_width + border_size
        top = self.__top_border__ - border_size
        bottom = self.__top_border__ + text_height + border_size

        heading_text_box_lines = [[left, top], [
            right, top], [right, bottom], [left, bottom]]

        pygame.draw.lines(
            framebuffer,
            colors.GREEN,
            True,
            heading_text_box_lines,
            2)

    def __render_ownship__(
        self,
        framebuffer: Surface
    ):
        """
        Draws the graphic for an aircraft, but always pointing straight up.
        This is to indicate our own aircraft, position, and heading
        which will always be straight up.

        Args:
            framebuffer {Surface} -- The render target.
        """
        points = self.__get_traffic_indicator__(
            self.__scope_center__,
            0,
            0)

        pygame.draw.polygon(framebuffer, colors.GREEN, points)

    def __draw_distance_rings__(
        self,
        framebuffer: Surface,
        scope_range: (int, int)
    ) -> int:
        """
        Draws rings that indicate how far out another aircraft is.
        Each ring represents 5 units. The spacing will always be
        the same no matter what the units are.

        Args:
            framebuffer {Surface} -- The render target.

        Returns:
            int: The distance (in pixels from the center to the first ring. Used for clutter control.)
        """

        max_distance = scope_range[0]
        step = scope_range[1]
        ring_distances = [max_distance]
        distance_units = configuration.CONFIGURATION.get_units()
        units_suffix = units.get_distance_unit_suffix(distance_units)
        half_pi = math.radians(45)
        sin_half_pi = math.sin(half_pi)
        cos_half_pi = math.cos(half_pi)
        ring_pixel_distances = []

        if step > 0:
            ring_distances = list(
                range(
                    step,
                    scope_range[0],
                    step))
            # To make it inclusive to the actual final ring
            # since range() does not include the last item.
            ring_distances.append(max_distance)

        for distance in ring_distances:
            radius_pixels = self.__get_pixel_distance__(distance, max_distance)
            pygame.draw.circle(
                framebuffer,
                colors.GREEN,
                self.__scope_center__,
                radius_pixels,
                2)
            ring_pixel_distances.append(radius_pixels)
            distance_text = "{}{}".format(
                int(distance),
                units_suffix)
            #pythag_dist = int(math.sqrt(2 * (radius_pixels * radius_pixels)))
            text_pos = [self.__scope_center__[0] + int(sin_half_pi * radius_pixels),
                        self.__scope_center__[1] - int(cos_half_pi * radius_pixels)]

            rendered_text, size = HudDataCache.get_cached_text_texture(
                distance_text,
                self.__font__,
                colors.GREEN,
                colors.BLACK,
                False,
                False)

            # Half size to reduce text clutter
            rendered_text = pygame.transform.scale(
                rendered_text,
                [size[0] >> 1, size[1] >> 1])

            framebuffer.blit(
                rendered_text,
                text_pos)
        return ring_pixel_distances[0]

    def __draw_compass_text__(
        self,
        framebuffer: Surface,
        our_heading: int,
        heading_to_draw: int,
        scope_range: int
    ):
        delta_angle = heading_to_draw - our_heading
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = wrap_angle(
            AdsbTopViewScope.ROTATION_PHASE_SHIFT + delta_angle)
        pixels_from_center = self.__get_pixel_distance__(
            scope_range, scope_range)

        screen_x, screen_y = self.__get_screen_projection_from_center__(
            delta_angle,
            pixels_from_center)

        heading_text, size = HudDataCache.get_cached_text_texture(
            str(heading_to_draw),
            self.__font__,
            colors.YELLOW,
            colors.BLACK,
            True,
            False)
        half_width = size[0] >> 1
        half_height = size[1] >> 1

        framebuffer.blit(
            heading_text,
            (screen_x - half_width, screen_y - half_height),
            special_flags=pygame.BLEND_RGBA_ADD)

    def __draw_all_compass_headings__(
        self,
        framebuffer: Surface,
        orientation: AhrsData,
        scope_range: int
    ):
        """
        Draw the text for ALL compass headings. 0, 90, 180, and 270
        This will make it clear that the scope is drawn user relative
        instead of absolute.

        Args:
            framebuffer (Surface): [description]
            orientation (AhrsData): [description]
        """
        our_heading = int(orientation.get_heading())
        [self.__draw_compass_text__(framebuffer, our_heading, heading_to_draw, scope_range)
         for heading_to_draw in [0, 90, 180, 270]]

    def __get_scope_range__(
        self,
        orientation: AhrsData
    ) -> (int, int):
        """
        Given a ground speed, figure out how far the scope should be.
        This is done by figuring out how far you will be in 10 minutes

        Args:
            orientation (AhrsData): [description]

        Returns:
            (int, int): The maximum distance the scope will cover and the distance between each ring.
        """
        self.range_timer.start()

        is_valid_groundspeed = orientation.groundspeed is not None and isinstance(
            orientation.groundspeed,
            Number)

        if not is_valid_groundspeed:
            return AdsbTopViewScope.DEFAULT_SCOPE_RANGE

        groundspeed = units.get_converted_units(
            configuration.CONFIGURATION.get_units(),
            orientation.groundspeed * units.yards_to_nm)

        if local_debug.is_debug() \
            and orientation.airspeed is not None \
            and isinstance(
                orientation.airspeed,
                Number):
            groundspeed = units.get_converted_units(
                configuration.CONFIGURATION.get_units(),
                orientation.airspeed * units.feet_to_nm)  # For debug only.

        distance_in_10_minutes = groundspeed / 6

        # The idea is to return the first range in the set
        # that is further than you will fly in 10 minutes.
        for possible_range in AdsbTopViewScope.SCOPE_RANGES:
            range_distance = possible_range[0]
            if range_distance > distance_in_10_minutes:
                self.range_timer.stop()

                return possible_range

        self.range_timer.stop()
        return self.__get_maximum_scope_range__()

    def __get_scope_zoom__(
        self,
        orientation: AhrsData
    ) -> (float, float):
        ideal_range = self.__get_scope_range__(orientation)
        self.__zoom_tracker__.set_target_zoom(ideal_range)

        return self.__zoom_tracker__.get_target_zoom()

    def render(
        self,
        framebuffer: Surface,
        orientation: AhrsData
    ):
        """
        Renders all of the on-screen reticles  for nearby traffic.

        Arguments:
            framebuffer {Surface} -- The render target.
            orientation {Orientation} -- The orientation of the plane the HUD is in.
        """

        # TODO: Investigate altitiude delta text
        # TODO: Try listing identifiers on side with lines leading to the aircraft
        # TODO: MORE TESTING!!!
        self.task_timer.start()

        scope_range = self.__get_scope_zoom__(orientation)

        self.__render_ownship__(framebuffer)

        self.rings_timer.start()
        self.__render_heading_text__(framebuffer, orientation)
        first_ring_pixel_radius = self.__draw_distance_rings__(
            framebuffer, scope_range)
        self.__draw_all_compass_headings__(
            framebuffer,
            orientation,
            scope_range[0])
        self.rings_timer.stop()

        # Get the traffic, and bail out of we have none
        self.bugs_timer.start()
        traffic_reports = HudDataCache.get_reliable_traffic()
        traffic_reports.sort(
            key=lambda traffic: traffic.distance,
            reverse=True)

        [self.__render_on_screen_target__(
            framebuffer, orientation, traffic, scope_range[0], first_ring_pixel_radius) for traffic in traffic_reports]
        self.bugs_timer.stop()

        self.task_timer.stop()


if __name__ == '__main__':
    from views.hud_elements import run_adsb_hud_element
    run_adsb_hud_element(AdsbTopViewScope)
