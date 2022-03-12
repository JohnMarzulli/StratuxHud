"""
Element to show targetting reticles for where traffic is.
"""

import math

from common_utils import fast_math
from common_utils.task_timer import TaskProfiler
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors, drawing

from views import hud_elements
from views.adsb_element import AdsbElement


class AdsbOnScreenReticles(AdsbElement):
    """
    Element to show targetting reticles for where traffic is.
    """

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

        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        reticle_cull_size = self.__width__ / 6
        self.__min_x__ = -reticle_cull_size
        self.__max_x__ = self.__width__ + reticle_cull_size
        self.__min_y__ = -reticle_cull_size
        self.__max_y__ = self.__height__ + reticle_cull_size

    def __get_onscreen_reticle__(
        self,
        scale: float,
        roll: float,
        rotation_center: list,
        reticle_center: list
    ) -> list:
        size = int(self.__height__ * scale)

        on_screen_reticle = [
            [0, -size],
            [size, 0],
            [0, size],
            [-size, 0]]

        # This rotation keeps the diamond points
        # vertical compared to the horizon
        on_screen_reticle = fast_math.rotate_points(
            on_screen_reticle,
            [0, 0],
            -2 * roll)

        # This moves it to where it would be in
        # screen space WITHOUT taking into account
        # aircraft roll
        on_screen_reticle = fast_math.translate_points(
            on_screen_reticle,
            reticle_center)

        # TODO - Figure out true POV and offset
        # This moves it into position to account
        # for the roll of the aircraft.
        on_screen_reticle = fast_math.rotate_points(
            on_screen_reticle,
            rotation_center,
            roll)

        return on_screen_reticle

    def __get_reticle_render_element__(
        self,
        orientation: AhrsData,
        rotation_center: list,
        traffic: Traffic
    ) -> drawing.HollowPolygon:
        """
        Draws a single reticle on the screen.

        Arguments:
            framebuffer {Surface} -- Render target
            orientation {Orientation} -- The orientation of the plane.
            traffic {Traffic} -- The traffic to draw the reticle for.
        """

        # Find where to draw the reticle....
        reticle_x, reticle_y = self.__get_traffic_projection__(
            orientation,
            traffic)

        if reticle_x is None or reticle_y is None:
            return None

        # Render using the Above us bug
        on_screen_reticle_scale = hud_elements.get_reticle_size(traffic.distance)
        reticle = self.__get_onscreen_reticle__(
            on_screen_reticle_scale,
            orientation.roll,
            rotation_center,
            [reticle_x, reticle_y])

        if reticle_x < self.__min_x__ or reticle_x > self.__max_x__:
            return None

        if reticle_y < self.__min_y__ or reticle_y > self.__max_y__:
            return None

        # Used for debugging reticle rotation
        # drawing.renderer.segment(
        #     framebuffer,
        #     colors.YELLOW,
        #     [reticle_x, reticle_y],
        #     reticle[0])

        # drawing.renderer.segment(
        #     framebuffer,
        #     colors.YELLOW,
        #     [reticle_x, reticle_y],
        #     rotation_center)

        return drawing.HollowPolygon(
            reticle,
            colors.RED,
            self.__line_width__,
            not self.__reduced_visuals__)

    def __get_rotation_point__(
        self,
        orientation: AhrsData
    ) -> list:
        """
        Get the coordinate for the lines for a given pitch and roll.

        Arguments:
            pitch {float} -- The pitch of the plane.
            roll {float} -- The roll of the plane.
            reference_angle {int} -- The pitch angle to be marked on the AH.

        Returns:
            [tuple] -- An array[4] of the X/Y line coords.
        """

        pitch_offset = self.__pixels_per_degree_y__ * -orientation.pitch

        roll_delta = 90 - orientation.roll

        radians = math.radians(roll_delta)

        center_x = self.__center_x__ - (pitch_offset * math.cos(radians)) + 0.5
        center_y = self.__center_y__ - (pitch_offset * math.sin(radians)) + 0.5

        return [center_x, center_y]

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

        with TaskProfiler('views.on_screen_reticles.AdsbOnScreenReticles.setup'):
            our_heading = orientation.get_onscreen_projection_heading()

            if isinstance(our_heading, str):
                return

            # Get the traffic, and bail out of we have none
            traffic_reports = HudDataCache.get_nearby_traffic()

            if traffic_reports is None:
                return

            traffic_reports = list(
                filter(
                    lambda x: not x.is_on_ground() and (math.fabs(our_heading - x.bearing) < 45),
                    traffic_reports))[:hud_elements.MAX_TARGET_BUGS]

            # find the position of the center of the 0 pitch indicator
            rotation_center = self.__get_rotation_point__(orientation)

            reticles = [self.__get_reticle_render_element__(
                orientation,
                rotation_center,
                traffic) for traffic in traffic_reports]

        with TaskProfiler('views.on_screen_reticles.AdsbOnScreenReticles.rendering'):
            # pylint:disable=expression-not-assigned
            [reticle.render(framebuffer) for reticle in reticles if reticle is not None]


if __name__ == '__main__':
    from views.artificial_horizon import ArtificialHorizon
    from views.hud_elements import run_hud_elements
    from views.roll_indicator import RollIndicator

    run_hud_elements([RollIndicator, ArtificialHorizon, AdsbOnScreenReticles])
