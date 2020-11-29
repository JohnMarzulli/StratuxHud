import math

import pygame
from common_utils import units
from common_utils.task_timer import TaskTimer
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from pygame import Surface
from rendering import colors

from views.adsb_element import AdsbElement
from views.hud_elements import wrap_angle


class AdsbTopViewScope(AdsbElement):
    MAXIMUM_DISTANCE = 20.0
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

        self.__top_border__ = int(self.__height__ * 0.05)
        self.__bottom_border__ = self.__height__ - self.__top_border__

        self.__draw_identifiers__ = True

        self.__adjustment__ = 0.0

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
        delta_angle = wrap_angle(
            AdsbTopViewScope.ROTATION_PHASE_SHIFT + delta_angle)

        # Find where to draw the reticle....
        screen_x, screen_y = self.__get_screen_projection_from_center__(
            delta_angle,
            pixels_from_center)

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
            rendered_text = pygame.transform.smoothscale(
                rendered_text,
                [size[0] >> 1, size[1] >> 1])

            framebuffer.blit(
                rendered_text,
                (screen_x, screen_y),
                special_flags=pygame.BLEND_RGBA_ADD)

    def __render_heading_text__(
        self,
        framebuffer,
        orientation: AhrsData
    ):
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
            self.__center__,
            0,
            0)

        pygame.draw.polygon(framebuffer, colors.GREEN, points)

    def __draw_distance_rings__(
        self,
        framebuffer: Surface
    ):
        """
        Draws rings that indicate how far out another aircraft is.
        Each ring represents 5 units. The spacing will always be
        the same no matter what the units are.

        Args:
            framebuffer {Surface} -- The render target.
        """
        for distance in [5, 10, 15, 20]:
            radius_pixels = self.__get_pixel_distance__(distance)
            pygame.draw.circle(
                framebuffer,
                colors.GREEN,
                self.__center__,
                radius_pixels,
                2)

    def __draw_compass_text__(
        self,
        framebuffer: Surface,
        our_heading: int,
        heading_to_draw: int
    ):
        delta_angle = heading_to_draw - our_heading
        # We need to rotate by 270 to make sure that
        # the orientation is correct AND to correct the phase.
        delta_angle = wrap_angle(
            AdsbTopViewScope.ROTATION_PHASE_SHIFT + delta_angle)
        pixels_from_center = self.__get_pixel_distance__(
            AdsbTopViewScope.MAXIMUM_DISTANCE)

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
        orientation: AhrsData
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
        [self.__draw_compass_text__(framebuffer, our_heading, heading_to_draw)
         for heading_to_draw in [0, 90, 180, 270]]

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

        self.__render_heading_text__(framebuffer, orientation)
        self.__render_ownship__(framebuffer)
        self.__draw_distance_rings__(framebuffer)
        self.__draw_all_compass_headings__(framebuffer, orientation)

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
