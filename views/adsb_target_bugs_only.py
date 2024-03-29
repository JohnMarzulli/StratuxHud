"""
View element to show target bugs for nearby aircraft.
"""

from common_utils.task_timer import TaskProfiler
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors, drawing

from views.adsb_element import AdsbElement
from views.hud_elements import (MAX_TARGET_BUGS, get_heading_bug_x,
                                get_reticle_size)


class AdsbTargetBugsOnly(AdsbElement):
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

    def __render_traffic_heading_bug__(
        self,
        traffic_report: Traffic,
        heading: float,
        ownship_altitude: int,
        framebuffer
    ):
        """
        Render a single heading bug to the framebuffer.

        Arguments:
            traffic_report {Traffic} -- The traffic we want to render a bug for.
            heading {int} -- Our current heading.
            ownship_altitude {int} -- Our plane's current altitude.
            framebuffer {Framebuffer} -- What we are going to draw to.
        """

        # Render using the Above us bug
        # target_bug_scale = 0.04
        target_bug_scale = get_reticle_size(traffic_report.distance)

        heading_bug_x = get_heading_bug_x(
            heading,
            traffic_report.bearing,
            self.__pixels_per_degree_x__)

        try:
            # TODO
            # Get any avaiable OWNSHIP data to make sure
            # that we are comparing pressure altitude to pressure altitude....
            # .. or use the Pressure Alt if that is available from the avionics.
            # .. or just validate that we are using pressure altitude...
            is_below = ownship_altitude > traffic_report.altitude
            reticle, reticle_edge_position_y = self.get_below_reticle(
                heading_bug_x,
                target_bug_scale) if is_below else self.get_above_reticle(
                    heading_bug_x,
                    target_bug_scale)

            bug_color = colors.BLUE if traffic_report.is_on_ground() else colors.RED

            drawing.renderer.polygon(framebuffer, bug_color, reticle)
        finally:
            pass

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        with TaskProfiler('views.adsb_target_bugs_only.AdsbTargetBugsOnly.setup'):
            heading = orientation.get_onscreen_projection_heading()

            if isinstance(heading, str):
                return

            # Get the traffic, and bail out of we have none
            traffic_reports = HudDataCache.get_nearby_traffic()

            if traffic_reports is None:
                return

            reports_to_show = traffic_reports[:MAX_TARGET_BUGS]

        # pylint:disable=expression-not-assigned
        with TaskProfiler('views.adsb_target_bugs_only.AdsbTargetBugsOnly.render'):
            [self.__render_traffic_heading_bug__(
                traffic_report,
                heading,
                orientation.alt,
                framebuffer) for traffic_report in reports_to_show]


if __name__ == '__main__':
    from views.compass_and_heading_bottom_element import \
        CompassAndHeadingBottomElement
    from views.hud_elements import run_hud_elements
    from views.roll_indicator import RollIndicator

    run_hud_elements([AdsbTargetBugsOnly, CompassAndHeadingBottomElement, RollIndicator])
