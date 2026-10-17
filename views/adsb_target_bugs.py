"""
Shows the "Info Cards" for ADSB information
"""

from common_utils.task_timer import TaskProfiler
from core_services import zoom_tracker
from data_sources.ahrs_data import AhrsData
from views.abstract_elements.adsb_element import AdsbElement
from views.adsb_target_bugs_only import get_relevant_traffic
from views.hud_elements import get_heading_bug_x


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
        reduced_visuals: bool = False,
    ):
        super().__init__(
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size,
            reduced_visuals,
        )

        self.__zoom_tracker__ = zoom_tracker.ZoomTracker()

        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)

    def __render_traffic_heading_bug__(
        self, traffic_report, heading, orientation, framebuffer
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
            heading, traffic_report.bearing, self.__pixels_per_degree_x__
        )

        additional_info_text = self.__get_additional_target_text__(
            traffic_report, orientation
        )

        self.__render_info_card__(
            framebuffer,
            str(traffic_report.get_display_name()),
            additional_info_text,
            heading_bug_x,
            traffic_report.get_age(),
        )

    def render(self, framebuffer, orientation: AhrsData):
        # Render a heading strip along the top

        self.__zoom_tracker__.update(orientation)

        with TaskProfiler("views.adsb_target_bugs.AdsbTargetBugs.setup"):
            heading = orientation.get_onscreen_projection_heading()

            if not orientation.gps_online:
                return

            reports_to_show = get_relevant_traffic(self.__zoom_tracker__)

        with TaskProfiler("views.adsb_target_bugs.AdsbTargetBugs.render"):
            # pylint:disable=expression-not-assigned
            [
                self.__render_traffic_heading_bug__(
                    traffic_report, heading, orientation, framebuffer
                )
                for traffic_report in reports_to_show
            ]


if __name__ == "__main__":
    from views.hud_elements import run_hud_element

    run_hud_element(AdsbTargetBugs)
