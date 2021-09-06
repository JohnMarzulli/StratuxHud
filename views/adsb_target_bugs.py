"""
Shows the "Info Cards" for ADSB information
"""

from common_utils.task_timer import TaskProfiler
from core_services import zoom_tracker
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache

from views.adsb_element import AdsbElement
from views.hud_elements import MAX_TARGET_BUGS, get_heading_bug_x


class AdsbTargetBugs(AdsbElement):
    """
    Shows the "Info Cards" for ADSB information
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
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)

    def __render_traffic_heading_bug__(
        self,
        traffic_report,
        heading,
        orientation,
        framebuffer
    ):
        """
        Render a single heading bug to the framebuffer.

        Arguments:
            traffic_report {Traffic} -- The traffic we want to render a bug for.
            heading {int} -- Our current heading.
            orientation {Orientation} -- Our plane's current orientation.
            framebuffer {Framebuffer} -- What we are going to draw to.
        """

        heading_bug_x = get_heading_bug_x(
            heading,
            traffic_report.bearing,
            self.__pixels_per_degree_x__)

        additional_info_text = self.__get_additional_target_text__(
            traffic_report,
            orientation)

        self.__render_info_card__(
            framebuffer,
            str(traffic_report.get_display_name()),
            additional_info_text,
            heading_bug_x,
            traffic_report.get_age())

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        # Render a heading strip along the top

        with TaskProfiler('views.adsb_target_bugs.AdsbTargetBugs.setup'):
            heading = orientation.get_onscreen_projection_heading()

            if not orientation.gps_online:
                return

            # Get the traffic, and bail out of we have none
            traffic_reports = HudDataCache.get_reliable_traffic()

            if traffic_reports is None:
                return

            reports_to_show = list(
                filter(
                    lambda x: zoom_tracker.INSTANCE.is_in_inner_range(
                        x.distance
                    )[0],
                    traffic_reports))

            # Draw the heading bugs in reverse order so the traffic closest to
            # us will be the most visible
            reports_to_show.sort(
                key=lambda traffic: traffic.distance,
                reverse=True)

            # Make sure only the closest bugs are rendered.
            reports_to_show = reports_to_show[:MAX_TARGET_BUGS]

        with TaskProfiler('views.adsb_target_bugs.AdsbTargetBugs.render'):
            # pylint:disable=expression-not-assigned
            [self.__render_traffic_heading_bug__(
                traffic_report,
                heading,
                orientation,
                framebuffer) for traffic_report in reports_to_show]


if __name__ == '__main__':
    from views.hud_elements import run_hud_element

    run_hud_element(AdsbTargetBugs)
