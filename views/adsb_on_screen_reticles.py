"""
Element to show targetting reticles for where traffic is.
"""

from common_utils import fast_math
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
        framebuffer_size
    ):
        super().__init__(
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size)

        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)

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

        # TODO - Figure out retical rotation better
        # TODO - Figure out true POV and offset
        # This moves it into position to account
        # for the roll of the aircraft.
        on_screen_reticle = fast_math.rotate_points(
            on_screen_reticle,
            rotation_center,
            roll)

        return on_screen_reticle

    def __render_on_screen_reticle__(
        self,
        framebuffer,
        orientation: AhrsData,
        rotation_center: list,
        traffic: Traffic
    ):
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
            return

        # Render using the Above us bug
        on_screen_reticle_scale = hud_elements.get_reticle_size(traffic.distance)
        reticle = self.__get_onscreen_reticle__(
            on_screen_reticle_scale,
            orientation.roll,
            rotation_center,
            [reticle_x, reticle_y])

        # Used for debugging reticle rotation
        # drawing.segment(
        #     framebuffer,
        #     colors.YELLOW,
        #     [reticle_x, reticle_y],
        #     reticle[0])

        # drawing.segment(
        #     framebuffer,
        #     colors.YELLOW,
        #     [reticle_x, reticle_y],
        #     rotation_center)

        self.__render_target_reticle__(
            framebuffer,
            reticle)

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

        center_x = self.__center_x__ - (pitch_offset * fast_math.cos(roll_delta)) + 0.5
        center_y = self.__center_y__ - (pitch_offset * fast_math.sin(roll_delta)) + 0.5

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

        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()

        traffic_reports = list(
            filter(
                lambda x: not x.is_on_ground(),
                traffic_reports))
        traffic_reports = traffic_reports[:hud_elements.MAX_TARGET_BUGS]

        # find the position of the center of the 0 pitch indicator
        rotation_center = self.__get_rotation_point__(orientation)

        # pylint:disable=expression-not-assigned
        [self.__render_on_screen_reticle__(
            framebuffer,
            orientation,
            rotation_center,
            traffic) for traffic in traffic_reports]

    def __render_target_reticle__(
        self,
        framebuffer,
        reticle_lines
    ):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """

        drawing.segments(
            framebuffer,
            colors.RED,
            True,
            reticle_lines,
            self.__line_width__)


if __name__ == '__main__':
    from views.artificial_horizon import ArtificialHorizon
    from views.hud_elements import run_hud_elements
    from views.roll_indicator import RollIndicator
    run_hud_elements([RollIndicator, ArtificialHorizon, AdsbOnScreenReticles])
