from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache

from views.adsb_element import AdsbElement, apply_declination
from views.hud_elements import MAX_TARGET_BUGS, get_heading_bug_x


class AdsbTargetBugs(AdsbElement):
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
            apply_declination(traffic_report.bearing),
            self.__pixels_per_degree_x__)

        additional_info_text = self.__get_additional_target_text__(
            traffic_report,
            orientation)

        try:
            self.__render_info_card__(
                framebuffer,
                str(traffic_report.get_display_name()),
                additional_info_text,
                heading_bug_x,
                traffic_report.get_age())
        except Exception as ex:
            print("EX:{}".format(ex))

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        # Render a heading strip along the top

        heading = orientation.get_onscreen_projection_heading()

        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()

        if traffic_reports is None:
            return

        # Draw the heading bugs in reverse order so the traffic closest to
        # us will be the most visible
        traffic_reports.sort(
            key=lambda traffic: traffic.distance,
            reverse=True)

        # Make sure only the closest bugs are rendered.
        traffic_reports = traffic_reports[:MAX_TARGET_BUGS]

        [self.__render_traffic_heading_bug__(
            traffic_report,
            heading,
            orientation,
            framebuffer) for traffic_report in traffic_reports]


if __name__ == '__main__':
    from views.hud_elements import run_hud_element

    run_hud_element(AdsbTargetBugs)
