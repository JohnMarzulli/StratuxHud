"""
View element for a weather "radar" that looks from the top downwards.
"""

import pygame

import math
from typing import Dict, Tuple

from common_utils.authoritative_time import get_system_time

from common_utils import fast_math, geo_math, units
from configuration import configuration
from core_services.scope_range import ScopeRange
from core_services.zoom_interpolation import SECONDS_FOR_ZOOM
from core_services.zoom_tracker import ZoomTracker
from data_sources.ahrs_data import AhrsData
from data_sources.airports import AirportClient
from rendering import colors, drawing
from views.abstract_elements.adsb_element import AdsbElement
from views.hud_elements import apply_declination

# -= Gratuitous eye-candy =-
##
# These constants control the appearence of the zooming in and out pulse
# effect. There are a lot of ways to tweak this for preferences and performance.

# How many pulses are spread evenly between the rings at once.
__ZOOM_PULSE_COUNT__ = 1
# Pulse speed: seconds for one pulse to travel from one ring to
# the other. Smaller is faster. Subclasses or instances may override.
__ZOOM_PULSE_SECONDS_PER_SWEEP__ = SECONDS_FOR_ZOOM
# Circles drawn per pulse, from the leading edge back to the tail.
__ZOOM_PULSE_TRAIL_STEPS__ = 10
# A "wave inside the wave": the strongest point travels through
# the pulse, starting at the trailing circle (the last to leave the
# starting ring) and moving forward to reach the leading circle as
# it arrives at the target ring.
# How many times that inner peak travels tail-to-head per sweep.
__ZOOM_PULSE_INNER_WAVES__ = 1
# How far the inner peak's glow spreads either side of it, as a
# fraction of the pulse length. Larger is a softer, wider peak.
__ZOOM_PULSE_PEAK_WIDTH__ = 0.35
# Strength of circles outside the inner peak, relative to the
# peak: 0.0 (invisible) to 1.0 (as strong as the peak).
__ZOOM_PULSE_EDGE_STRENGTH__ = 0.15
# Fraction of the zoom spent fading the whole effect in at the
# start and out at the end. Kept short so the inner peak is still
# bright when it arrives at the target ring.
__ZOOM_PULSE_FADE__ = 0.1
# Gap between the circles that make up a pulse, as a multiple of
# the scope's thin line width.
__ZOOM_PULSE_CIRCLE_SPACING__ = 4  # 3
# Thickness of each circle in a pulse, as a multiple of the
# scope's thin line width.
__ZOOM_PULSE_CIRCLE_THICKNESS__ = 4  # 4 #2
# Peak opacity of the pulse, 0.0 (invisible) to 1.0 (solid).
# Lower values let the weather/traffic underneath show through.
__ZOOM_PULSE_OPACITY__ = 0.6


class TopDownScope(AdsbElement):
    """
    A view element for the HUD that draws a radar style scope
    showing graphics relative to our current position.
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
        reduced_visuals: bool = False,
    ):
        super().__init__(
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size,
            reduced_visuals,
        )

        self.__zoom_tracker__ = ZoomTracker()
        self.__draw_identifiers__ = True

        self.__adjustment__ = 0.0

        # Make the center of the scope towards the bottome of the screen
        # such that we can see aircraft sneeking up behind us, but not so much
        # that we loose to much fidelity in front of us.
        self.__scope_center__ = [
            self.__center_x__,
            self.__center_y__ + int(self.__center_y__ >> 1),
        ]

        size = self.__framebuffer_size__[1] * 0.04
        half_size = int((size / 2.0) + 0.5)
        quarter_size = int((size / 4.0) + 0.5)
        self.__no_direction_target_size__ = quarter_size
        self.__line_width__ = max(1, self.__line_width__ >> 1)

        # 1 - Come up with the 0,0 based line coordinates
        self.__target_indicator__ = [
            [-quarter_size, half_size],
            [0, -half_size],
            [quarter_size, half_size],
        ]

    def __get_traffic_indicator__(
        self, indicator_position: list, our_heading: float, traffic_heading: float
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
        rotation_degrees = int(fast_math.wrap_degrees(rotation + self.__adjustment__))

        # 3 - Rotate the zero-based points
        radians = math.radians(rotation_degrees)
        rotation_sin = math.sin(radians)
        rotation_cos = math.cos(radians)
        rotated_points = [
            [
                point[0] * rotation_cos - point[1] * rotation_sin,
                point[0] * rotation_sin + point[1] * rotation_cos,
            ]
            for point in self.__target_indicator__
        ]

        # 4 - Translate to the bug center point
        return [
            [point[0] + indicator_position[0], point[1] + indicator_position[1]]
            for point in rotated_points
        ]

    def __get_pixel_distance__(
        self, distance_in_user_units: float, scope_range: ScopeRange
    ) -> int:
        max_pixel_distance = self.__scope_center__[1] - self.__top_border__

        proportion = distance_in_user_units / scope_range.max_ring_range
        return int(max_pixel_distance * proportion)

    def __get_precise_screen_coordinates__(
        self,
        orientation: AhrsData,
        current_heading: float,
        scope_range: ScopeRange,
        gps_coordinates,
    ) -> Tuple[float, float]:
        """
        Same as __get_screen_coordinates__, but keeps sub-pixel precision.
        Snapping each vertex to whole pixels makes large shapes
        visibly wobble as our aircraft moves.
        """
        distance = geo_math.get_distance(orientation.position, gps_coordinates)
        bearing = geo_math.get_bearing(orientation.position, gps_coordinates)
        radians = math.radians(
            TopDownScope.TRAFFIC_PHASE_SHIFT + bearing - current_heading
        )

        max_pixel_distance = self.__scope_center__[1] - self.__top_border__
        pixel_distance = max_pixel_distance * (distance / scope_range.max_ring_range)

        return (
            (math.cos(radians) * pixel_distance) + self.__scope_center__[0],
            (math.sin(radians) * pixel_distance) + self.__scope_center__[1],
        )

    def __get_screen_projection_from_center__(
        self, angle_degrees: float, distance_pixels: float
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

    def __render_ownship__(self, framebuffer: pygame.Surface):
        """
        Draws the graphic for an aircraft, but always pointing straight up.
        This is to indicate our own aircraft, position, and heading
        which will always be straight up.

        Args:
            framebuffer {pygame.Surface} -- The render target.
        """
        points = self.__get_traffic_indicator__(self.__scope_center__, 0, 0)

        drawing.renderer.polygon(
            framebuffer, colors.GREEN, points, not self.__reduced_visuals__
        )

    def __get_screen_coordinates__(
        self,
        orientation: AhrsData,
        current_heading,
        scope_range: ScopeRange,
        gps_coordinates,
    ):
        distance_start = geo_math.get_distance(orientation.position, gps_coordinates)
        bearing = geo_math.get_bearing(orientation.position, gps_coordinates)
        delta_angle = bearing - current_heading
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = TopDownScope.TRAFFIC_PHASE_SHIFT + delta_angle
        delta_angle = fast_math.wrap_degrees(delta_angle)

        pixel_distance = self.__get_pixel_distance__(distance_start, scope_range)

        return self.__get_screen_projection_from_center__(delta_angle, pixel_distance)

    def __draw_zoom_pulse__(
        self,
        framebuffer: pygame.Surface,
        scope_range: ScopeRange,
        zoom_progress,
        ring_color=colors.GREEN,
    ):
        """
        Draws glowing bands that sweep between the center ring and the
        outer ring while a zoom is in progress. Zooming in, the bands
        start at the center ring and travel outward to the outer ring
        (things are spreading apart); zooming out, they start at the
        outer ring and travel inward to the center ring (things are
        being pulled together).

        Args:
            framebuffer (pygame.Surface): The render target.
            scope_range (ScopeRange): The range currently displayed.
            zoom_progress: None, or (proportion complete, direction)
                where direction is 1 for zooming out, -1 for zooming in.
            ring_color: The base color of the glow.
        """
        if zoom_progress is None:
            return

        proportion, direction = zoom_progress

        # Briefly fade the whole effect in and out so it does not pop
        # on or off, while staying at full strength through the middle.
        fade = max(0.001, __ZOOM_PULSE_FADE__)
        envelope = fast_math.clamp(
            0.0, min(proportion, 1.0 - proportion) / fade, 1.0
        )

        if envelope <= 0.0:
            return

        inner_radius = self.__get_pixel_distance__(
            scope_range.center_ring_range, scope_range
        )
        outer_radius = self.__get_pixel_distance__(
            scope_range.max_ring_range, scope_range
        )
        span = outer_radius - inner_radius

        if span <= 0:
            return

        spacing = max(
            1, int(self.__thin_line_width__ * __ZOOM_PULSE_CIRCLE_SPACING__)
        )
        width = max(
            1, int(self.__thin_line_width__ * __ZOOM_PULSE_CIRCLE_THICKNESS__)
        )
        bright_color = colors.get_color_mix(ring_color, colors.WHITE, 0.5)
        steps = __ZOOM_PULSE_TRAIL_STEPS__
        max_alpha = 255 * fast_math.clamp(0.0, __ZOOM_PULSE_OPACITY__, 1.0)
        # (rgba, radius, width) for each circle, drawn in order.
        circles = []

        sweeps_completed = (proportion * SECONDS_FOR_ZOOM) / max(
            0.01, __ZOOM_PULSE_SECONDS_PER_SWEEP__
        )

        for pulse in range(__ZOOM_PULSE_COUNT__):
            phase = (sweeps_completed + pulse / __ZOOM_PULSE_COUNT__) % 1.0

            # Zooming in (direction -1): center ring -> outer ring.
            # Zooming out (direction 1): outer ring -> center ring.
            travel = phase if direction < 0 else 1.0 - phase
            leading_radius = inner_radius + (travel * span)
            step_strengths = self.__get_zoom_pulse_strengths__(steps, phase)

            pulse_circles = []

            for step in range(steps):
                # The trail sits behind the leading edge, i.e. opposite
                # the direction of travel. Clipping it to the rings makes
                # the wave grow out of its starting ring and sink into
                # its ending ring.
                radius = leading_radius + (step * spacing * direction)

                if radius < inner_radius or radius > outer_radius:
                    continue

                strength = step_strengths[step]
                alpha = int(max_alpha * envelope * strength)

                if alpha <= 0:
                    continue

                # The strongest circles also shift toward white.
                base = colors.get_color_mix(ring_color, bright_color, strength)

                pulse_circles.append(
                    (strength, ([base[0], base[1], base[2], alpha], int(radius), width))
                )

            # Weakest first, strongest last, so the strongest circle
            # wins wherever circles overlap.
            pulse_circles.sort(key=lambda entry: entry[0])
            circles.extend(circle for _, circle in pulse_circles)

        drawing.renderer.translucent_circles(
            framebuffer, self.__scope_center__, circles
        )

    def __get_zoom_pulse_strengths__(self, steps: int, phase: float) -> list:
        """
        Returns the relative strength [0.0, 1.0] of each circle in a
        pulse, from the leading edge (index 0) to the trailing edge.

        A smooth peak travels from the trailing circle to the leading
        circle as the pulse sweeps (phase 0.0 -> 1.0), so the strongest
        circle reaches the target ring first.

        Args:
            steps (int): How many circles are in the pulse.
            phase (float): How far through its sweep the pulse is [0.0, 1.0).
        """
        if steps <= 0:
            return []

        edge = fast_math.clamp(0.0, __ZOOM_PULSE_EDGE_STRENGTH__, 1.0)
        peak_width = max(0.01, __ZOOM_PULSE_PEAK_WIDTH__)
        inner_phase = (phase * max(1, __ZOOM_PULSE_INNER_WAVES__)) % 1.0
        # 1.0 is the trailing circle, 0.0 the leading circle.
        peak = 1.0 - inner_phase
        strengths = []

        for step in range(steps):
            position = step / (steps - 1) if steps > 1 else 0.0
            distance = abs(position - peak) / peak_width

            # Raised cosine bump: 1.0 at the peak, easing to 0.0
            # at peak_width away.
            shape = (
                0.5 + (0.5 * math.cos(math.pi * distance)) if distance < 1.0 else 0.0
            )

            strengths.append(edge + ((1.0 - edge) * shape))

        return strengths

    def __draw_distance_rings__(
        self,
        framebuffer: pygame.Surface,
        scope_range: ScopeRange,
        ring_color=colors.GREEN,
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

        distance_units = configuration.CONFIGURATION.get_units()
        units_suffix = units.get_distance_unit_suffix(distance_units)
        ring_pixel_distances = []
        ring_distances = [scope_range.center_ring_range, scope_range.max_ring_range]

        radians = math.radians(30)
        sin_text_placement = math.sin(radians)
        cos_text_placement = math.cos(radians)

        for distance in ring_distances:
            radius_pixels = self.__get_pixel_distance__(distance, scope_range)

            if not self.__reduced_visuals__:
                drawing.renderer.circle(
                    framebuffer,
                    colors.BLACK,
                    self.__scope_center__,
                    radius_pixels,
                    self.__thin_line_width__ * 4,
                    True,
                )

            drawing.renderer.circle(
                framebuffer,
                ring_color,
                self.__scope_center__,
                radius_pixels,
                self.__thin_line_width__,
                not self.__reduced_visuals__,
            )  # AA circle costs a BUNCH on the Pi

            ring_pixel_distances.append(radius_pixels)

            text_x = self.__scope_center__[0] + int(sin_text_placement * radius_pixels)
            text_y = self.__scope_center__[1] - int(cos_text_placement * radius_pixels)

            range_text: str = (
                str(int(distance)) if distance >= 1.0 else "{:.1f}".format(distance)
            )

            self.__render_text_with_stacked_annotations__(
                framebuffer,
                [text_x, text_y],
                [
                    [1.0, range_text, colors.GREEN],
                    [0.5, units_suffix, colors.GREEN],
                ],
            )

        return ring_pixel_distances[0]

    def __draw_compass_text__(
        self,
        framebuffer: pygame.Surface,
        our_heading: int,
        heading_to_draw: int,
        scope_range: ScopeRange,
    ):
        delta_angle = heading_to_draw - our_heading
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = fast_math.wrap_degrees(
            TopDownScope.ROTATION_PHASE_SHIFT + delta_angle
        )
        pixels_from_center = self.__get_pixel_distance__(
            scope_range.max_ring_range, scope_range
        )

        screen_x, screen_y = self.__get_screen_projection_from_center__(
            apply_declination(delta_angle), pixels_from_center
        )

        heading_text_rotation = -(heading_to_draw - our_heading)
        heading_mark_rotation = -heading_text_rotation + 180

        if self.__cluter_visuals__:
            indicator_mark_ends = fast_math.rotate_points(
                [[0, int(self.__line_width__ * -5)]],
                [0, 0],
                apply_declination(heading_mark_rotation),
            )

            indicator_mark_ends = fast_math.translate_points(
                indicator_mark_ends, [screen_x, screen_y]
            )

            drawing.renderer.segment(
                framebuffer,
                colors.GREEN,
                [screen_x, screen_y],
                indicator_mark_ends[0],
                self.__line_width__,
                not self.__reduced_visuals__,
            )

        display_text = int(
            fast_math.wrap_degrees(TopDownScope.TEXT_PHASE_SHIFT + heading_to_draw)
        )
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
                True,
            )

        self.__render_centered_text__(
            framebuffer,
            str(display_text),
            (screen_x, screen_y),
            colors.YELLOW,
            colors.BLACK,
            1.0,
            0,
            not self.__reduced_visuals__,
        )

    def __draw_all_compass_headings__(
        self,
        framebuffer: pygame.Surface,
        orientation: AhrsData,
        scope_range: ScopeRange,
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
                framebuffer, our_heading, heading_to_draw, scope_range
            )

    def __draw_airports__(self, framebuffer, orientation, scope_range: ScopeRange):
        is_airport_data_valid = AirportClient.is_airport_data_valid()

        if not is_airport_data_valid and get_system_time().second % 2 == 0:
            self.__render_text_right_justified__(
                framebuffer,
                "EXPIRED",
                [self.__right_border__, self.__bottom_border__ - self.__font_height__],
                colors.RED,
            )

        if (
            orientation is None
            or orientation.position is None
            or orientation.position[0] is None
            or orientation.position[1] is None
        ):
            return

        nearby_airports = AirportClient.get_nearby_airports()

        [
            self.__render_airport_target__(
                framebuffer, orientation, nearby_airports[airport_id], scope_range
            )
            for airport_id in nearby_airports
        ]

    def __render_airport_target__(
        self,
        framebuffer,
        orientation: AhrsData,
        airport: Dict[str, any],
        scope_range: ScopeRange,
    ):
        """
        Draws a single reticle on the screen.

        Arguments:
            framebuffer {pygame.Surface} -- Render target
            orientation {Orientation} -- The orientation of the plane.
            airport {Dict[str, any]} -- The airport to draw the reticle for.
            first_ring_pixel_distance {int} -- The distance (in pixels) from the ownship to the first scope ring. Used for clutter control.
        """

        # Airport data format:
        # {"coordinates":{"longitude":-122.149561389,"latitude":47.280656111},"ident":"WA84","name":"Auburn Academy","airportType":"AD","isPublic":false}

        airport_position = [
            airport["coordinates"]["longitude"],
            airport["coordinates"]["latitude"],
        ]

        # This position comes as lon/lat
        # All supporting code needs to be provided in lat/lon
        correct_airport_position = [
            airport_position[1],
            airport_position[0],
        ]

        gps_distance = geo_math.get_distance(
            orientation.position, correct_airport_position
        )

        if gps_distance > scope_range.max_ring_range:
            return

        screen_x, screen_y = self.__get_screen_coordinates__(
            orientation,
            orientation.get_precise_gps_heading(),
            scope_range,
            correct_airport_position,
        )

        if screen_x < 0 or screen_x > self.__width__:
            return

        if screen_y < 0 or screen_y > self.__height__:
            return

        target_color = self.__get_airport_color__(airport)

        drawing.renderer.filled_circle(
            framebuffer,
            target_color,
            [screen_x, screen_y],
            self.__no_direction_target_size__,
            not self.__reduced_visuals__,
        )

        if gps_distance > scope_range.center_ring_range:
            return

        angle_to_airport = geo_math.get_bearing(
            orientation.position, correct_airport_position
        )
        relative_angle: float = angle_to_airport - orientation.get_precise_gps_heading()

        should_draw_identifier: bool = self.__should_draw_identifier__(
            relative_angle, gps_distance, scope_range)

        if self.__draw_identifiers__ and should_draw_identifier:
            identifier = airport["ident"]

            self.__render_centered_text__(
                framebuffer,
                identifier,
                [screen_x, screen_y + (self.__no_direction_target_size__ << 2)],
                target_color,
                colors.BLACK,
                0.5,
                0,
                True,
            )

    def __should_draw_identifier__(
            self,
            relative_angle: float,
            distance_to_target: float,
            scope_range: ScopeRange
    ):
        relative_angle = math.fabs(relative_angle)

        # The intent is to still show airports and planes that are really close to us
        # but then hide them if they are too far away and outside the forward view.
        secret_inner_circle_range: float = scope_range.center_ring_range / 2.0
        relative_angle = math.fabs(relative_angle)

        return (relative_angle < 90.0) or (distance_to_target < secret_inner_circle_range)

    def __get_airport_color__(self, airport: Dict[str, any]):
        if "flightRules" not in airport:
            return colors.WHITE  # TODO - Find a way to determine if it has a tower

        flight_rules = airport["flightRules"]

        if flight_rules == "VFR":
            return colors.GREEN
        elif flight_rules == "MVFR":
            return colors.BLUE
        elif flight_rules == "IFR":
            return colors.RED
        elif flight_rules == "LIFR":
            return colors.MAGENTA

        return colors.GRAY
