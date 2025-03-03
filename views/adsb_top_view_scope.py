"""
View element for a "radar scope" that looks from the top downwards.
"""

import pygame

from common_utils import fast_math, geo_math
from common_utils.task_timer import TaskProfiler
from configuration import configuration
from core_services import breadcrumbs, zoom_tracker
from core_services.scope_range import ScopeRange
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.nexrad import NexradClient
from data_sources.traffic import Traffic
from rendering import colors, drawing
from views.top_down_scope import TopDownScope


class AdsbTopViewScope(TopDownScope):
    """
    A view element for the HUD that draws a radar style scope
    showing where traffic is relative to our current position.
    """

    def handle_events(self, unhandled_events) -> list:
        remaining_unhandled_events = []

        for event in unhandled_events:
            if event.type != pygame.KEYUP:
                continue

            if event.key in [pygame.K_UP, pygame.K_KP8]:
                zoom_tracker.INSTANCE.manual_zoom_out()
            elif event.key in [pygame.K_DOWN, pygame.K_KP2]:
                zoom_tracker.INSTANCE.manual_zoom_in()
            elif event.key in [pygame.K_KP7, 55]:  # 55 is '7'
                zoom_tracker.INSTANCE.return_to_automatic()
            else:
                remaining_unhandled_events.append(event)

        return remaining_unhandled_events

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

    def __render_on_screen_target__(
        self,
        framebuffer,
        orientation: AhrsData,
        traffic: Traffic,
        scope_range: ScopeRange,
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

        (is_within_threshold, display_distance) = (
            zoom_tracker.INSTANCE.is_in_inner_range(traffic.distance)
        )

        if not is_within_threshold:
            return

        pixels_from_center = self.__get_pixel_distance__(display_distance, scope_range)

        delta_angle = orientation.get_onscreen_gps_heading()
        delta_angle = traffic.bearing - delta_angle
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = AdsbTopViewScope.TRAFFIC_PHASE_SHIFT + delta_angle
        delta_angle = fast_math.wrap_degrees(delta_angle)

        # Find where to draw the reticle....
        screen_x, screen_y = self.__get_screen_projection_from_center__(
            delta_angle, pixels_from_center
        )

        if screen_x < 0 or screen_x > self.__width__:
            return

        if screen_y < 0 or screen_y > self.__height__:
            return

        target_color = colors.BLUE if traffic.is_on_ground() else colors.RED

        if traffic.track is not None:
            points = self.__get_traffic_indicator__(
                [screen_x, screen_y],
                orientation.get_onscreen_gps_heading(),
                traffic.track,
            )
            drawing.renderer.polygon(
                framebuffer, target_color, points, not self.__reduced_visuals__
            )
        else:
            drawing.renderer.filled_circle(
                framebuffer,
                target_color,
                [screen_x, screen_y],
                self.__no_direction_target_size__,
                not self.__reduced_visuals__,
            )

        # Do not draw identifier text for any targets further than
        # the first scope ring.
        if pixels_from_center > scope_range.center_ring_range:
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
                True,
            )

            altitude_text = traffic.get_altitude_delta_text(orientation)

            self.__render_centered_text__(
                framebuffer,
                altitude_text,
                [
                    screen_x,
                    screen_y
                    + self.__font_half_height__
                    + (self.__no_direction_target_size__ << 2),
                ],
                colors.YELLOW,
                colors.BLACK,
                0.5,
                0,
                True,
            )

    def __render_breadcrumbs__(
        self,
        framebuffer: pygame.Surface,
        scope_range: ScopeRange,
        orientation: AhrsData,
    ):
        breadcrumb_reports = breadcrumbs.INSTANCE.get_trail()
        breadcrumb_count = len(breadcrumb_reports)

        if (
            orientation.position is None
            or orientation.position[0] is None
            or orientation.position[1] is None
        ):
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

            distance_start = geo_math.get_distance(
                orientation.position, breadcrumb_reports[index][0]
            )

            if distance_start > scope_range.max_ring_range:
                previous_position = None
                continue

            bearing = geo_math.get_bearing(
                orientation.position, breadcrumb_reports[index][0]
            )
            delta_angle = bearing - current_heading
            # We need to rotate by 270 to make sure that
            # the orientation is correct AND to correct the phase.
            delta_angle = AdsbTopViewScope.TRAFFIC_PHASE_SHIFT + delta_angle
            delta_angle = fast_math.wrap_degrees(delta_angle)

            pixel_distance = self.__get_pixel_distance__(distance_start, scope_range)

            color = [int(component * proportion) for component in colors.GREEN]
            screen_coords = self.__get_screen_projection_from_center__(
                delta_angle, pixel_distance
            )

            if previous_position is not None:
                drawing.renderer.segment(
                    framebuffer,
                    color,
                    previous_position,
                    screen_coords,
                    width=self.__line_width__,
                )

            previous_position = screen_coords

        # Complete the loop
        if previous_position is not None:
            drawing.renderer.segment(
                framebuffer,
                colors.GREEN,
                previous_position,
                self.__scope_center__,
                width=self.__line_width__,
            )

    def render(self, framebuffer: pygame.Surface, orientation: AhrsData):
        """
        Renders all of the on-screen reticles  for nearby traffic.

        Arguments:
            framebuffer {pygame.Surface} -- The render target.
            orientation {Orientation} -- The orientation of the plane the HUD is in.
        """

        # TODO: Investigate altitiude delta text
        # TODO: Try listing identifiers on side with lines leading to the aircraft
        # TODO: MORE TESTING!!!

        with TaskProfiler("views.adsb_top_view_scope.AdsbTopViewScope.setup"):
            scope_range: ScopeRange = zoom_tracker.INSTANCE.get_target_zoom()
            traffic_reports = HudDataCache.get_reliable_traffic()
            traffic_reports.sort(key=lambda traffic: traffic.distance, reverse=True)

        scope_range = zoom_tracker.INSTANCE.get_target_zoom()

        with TaskProfiler(
            "views.adsb_top_view_scope.AdsbTopViewScope.render_breadcrumbs"
        ):
            self.__render_breadcrumbs__(framebuffer, scope_range, orientation)

        with TaskProfiler("views.adsb_top_view_scope.AdsbTopViewScope.render_rings"):

            first_ring_pixel_radius = self.__draw_distance_rings__(
                framebuffer, scope_range
            )

            self.__draw_all_compass_headings__(framebuffer, orientation, scope_range)

            self.__render_ownship__(framebuffer)

        if not orientation.gps_online:
            return

        with TaskProfiler("views.adsb_top_view_scope.AdsbTopViewScope.render_airports"):

            self.__draw_airports__(framebuffer, orientation, scope_range)

        with TaskProfiler("views.adsb_top_view_scope.AdsbTopViewScope.render_traffic"):

            # pylint: disable=expression-not-assigned
            [
                self.__render_on_screen_target__(
                    framebuffer, orientation, traffic, scope_range
                )
                for traffic in traffic_reports
            ]


if __name__ == "__main__":
    from views.compass_and_heading_top_element import CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements

    nexrad_client = NexradClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )

    run_hud_elements([AdsbTopViewScope, CompassAndHeadingTopElement, Groundspeed])
