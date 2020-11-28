import math
from views import target_count

import pygame
from common_utils import units
from common_utils.task_timer import TaskTimer
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors

from views.adsb_element import AdsbElement
from views.hud_elements import wrap_angle


class AdsbTopViewScope(AdsbElement):
    MAXIMUM_DISTANCE = 20.0

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

        self.__top_border__ = int(self.__height__ * 0.05)
        self.__bottom_border__ = self.__height__ - self.__top_border__

        self.__draw_identifiers__ = False

    def __get_display_units__(
        self
    ):
        display_units = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY,
            units.STATUTE)

        return display_units

    def __get_pixel_distance__(
        self,
        distance_in_user_units: float
    ) -> int:
        max_pixel_distance = self.__center__[1] - self.__top_border__

        if distance_in_user_units > AdsbTopViewScope.MAXIMUM_DISTANCE:
            return max_pixel_distance

        proportion = distance_in_user_units / AdsbTopViewScope.MAXIMUM_DISTANCE
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
        screen_x = (reticle_x * distance_pixels) + self.__center__[0]
        screen_y = (reticle_y * distance_pixels) + self.__center__[1]

        return (int(screen_x), int(screen_y))

    def __render_on_screen_target__(
        self,
        framebuffer,
        orientation: AhrsData,
        traffic: Traffic
    ):
        """
        Draws a single reticle on the screen.

        Arguments:
            framebuffer {Surface} -- Render target
            orientation {Orientation} -- The orientation of the plane.
            traffic {Traffic} -- The traffic to draw the reticle for.
        """

        display_distance = units.get_converted_units(
            self.__get_display_units__(),
            traffic.distance)

        if display_distance > AdsbTopViewScope.MAXIMUM_DISTANCE:
            return

        pixels_from_center = self.__get_pixel_distance__(display_distance)

        delta_angle = orientation.get_heading()
        delta_angle = traffic.bearing - delta_angle
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = wrap_angle(270 + delta_angle)

        # Find where to draw the reticle....
        screen_x, screen_y = self.__get_screen_projection_from_center__(
            delta_angle,
            pixels_from_center)
        
        target_color = colors.BLUE if traffic.is_on_ground() == True else colors.RED

        pygame.draw.circle(
            framebuffer,
            target_color,
            (screen_x, screen_y),
            4,
            4)

        if self.__draw_identifiers__:
            identifier = traffic.get_display_name()

            rendered_text, size = HudDataCache.get_cached_text_texture(
                identifier,
                self.__font__,
                colors.YELLOW,
                colors.BLACK,
                True,
                False)

            framebuffer.blit(
                rendered_text,
                (screen_x, screen_y),
                special_flags=pygame.BLEND_RGBA_ADD)

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        """
        Renders all of the on-screen reticles  for nearby traffic.

        Arguments:
            framebuffer {Surface} -- The render target.
            orientation {Orientation} -- The orientation of the plane the HUD is in.
        """

        # TODO: Get running under debug
        # TODO: Position text better (like info cards)
        # TODO: Use a visual that implies direction
        # TODO: Rotate symbol to show direction
        # TODO: Draw aircraft symbol in the middle
        # TODO: Add altitiude delta text
        # TODO: TEST!!!

        pygame.draw.circle(
            framebuffer,
            colors.GREEN,
            self.__center__,
            2,
            2)

        for distance in [5, 10, 15, 20]:
            radius_pixels = self.__get_pixel_distance__(distance)
            pygame.draw.circle(
                framebuffer,
                colors.GREEN,
                self.__center__,
                radius_pixels,
                2)

        for heading in [0, 90, 180, 270]:
            delta_angle = orientation.get_heading()
            delta_angle = heading - delta_angle
            # We need to rotate by 270 to make sure that
            # the orientation is correct AND to correct the phase.
            delta_angle = wrap_angle(270 + delta_angle)
            pixels_from_center = self.__get_pixel_distance__(
                AdsbTopViewScope.MAXIMUM_DISTANCE)

            screen_x, screen_y = self.__get_screen_projection_from_center__(
                delta_angle,
                pixels_from_center)

            heading_text, size = HudDataCache.get_cached_text_texture(
                str(heading),
                self.__font__,
                colors.YELLOW,
                colors.BLACK,
                True,
                False)
            half_width = size[0] >> 1
            half_height = size[1] >> 1

            framebuffer.blit(
                heading_text,
                (screen_x - half_width, screen_y - half_height))

        self.task_timer.start()
        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()
        traffic_reports.sort(
            key=lambda traffic: traffic.distance,
            reverse=True)

        [self.__render_on_screen_target__(
            framebuffer, orientation, traffic) for traffic in traffic_reports]

        self.task_timer.stop()


if __name__ == '__main__':
    from views.hud_elements import run_adsb_hud_element
    run_adsb_hud_element(AdsbTopViewScope)
