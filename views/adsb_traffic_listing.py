"""
View that shows the list of nearby traffic
"""

from typing import List

from common_utils import units
from common_utils.text_pagination import get_lines_grouped_by_page
from data_sources.ahrs_data import NOT_AVAILABLE, AhrsData
from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors
from views.abstract_elements.adsb_element import apply_declination
from views.abstract_elements.paginated_text_element import PaginatedTextElement
from views.abstract_elements.text_line import TextLine


class AdsbTrafficListing(PaginatedTextElement):
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

        self.__font_scale__ = 0.75
        self.__max_screen_lines__ -= 2

    def __get_text_pages__(self, orientation: AhrsData) -> List[List[TextLine]]:
        reports_to_show = HudDataCache.get_reliable_traffic()

        if reports_to_show is None:
            return []

        # We do not want to show traffic on the ground.
        reports_to_show = list(filter(lambda x: not x.is_on_ground(), reports_to_show))
        reports_to_show = sorted(reports_to_show, key=lambda x: x.distance)

        all_report_text: List[str] = [
            self.__get_report_text__(report, orientation) for report in reports_to_show
        ]

        pageless_reports = []
        index: int = 0

        for report in all_report_text:
            pageless_reports.append(TextLine(self.__get_row_color__(index), report))
            index += 1

        return get_lines_grouped_by_page(
            pageless_reports, self.__get_page_header__(), self.__max_screen_lines__
        )

    def __get_page_header__(self) -> TextLine:
        return TextLine(
            colors.WHITE,
            self.__get_justified_line__(
                "IDENT", "DIST", "SPEED", "HEAD", "BEAR", "ALT", "DELTA"
            ),
        )

    def __get_report_text__(self, traffic: Traffic, orientation: AhrsData):
        identifier = str(traffic.get_display_name())
        display_alt = int(traffic.altitude)
        speed_text = (
            self.__get_distance_string_without_units__(
                traffic.speed * units.yards_to_sm
            )
            if orientation.gps_online
            else NOT_AVAILABLE
        )
        speed_text = speed_text.split(".")[0]
        distance_text = (
            self.__get_distance_string_without_units__(traffic.distance)
            if orientation.gps_online
            else NOT_AVAILABLE
        )
        altitude_text = "{0}".format(display_alt)
        bearing_text = (
            "{0:.0f}".format(apply_declination(traffic.bearing))
            if orientation.gps_online
            else NOT_AVAILABLE
        )
        heading_text = (
            "{0:.0f}".format(apply_declination(traffic.track))
            if orientation.gps_online
            else NOT_AVAILABLE
        )
        alt_delta = (
            int(((display_alt - orientation.alt) / 100) + 0.5)
            if orientation.alt != "---"
            else "---"
        )
        alt_sign = "+" if alt_delta != "---" and alt_delta >= 0 else ""
        delta_text = "{0}{1}".format(alt_sign, alt_delta)

        return self.__get_justified_line__(
            identifier,
            distance_text,
            speed_text,
            heading_text,
            bearing_text,
            altitude_text,
            delta_text,
        )

    def __get_justified_line__(
        self,
        identifier: str,
        distance: str,
        speed: str,
        heading: str,
        bearing: str,
        altitude: str,
        delta: str,
    ):
        identifier_name_slice_length: int = 8
        distance_text_slice_length: int = 5
        speed_text_slice_length: int = 5
        bearing_slice_length: int = 4
        altitude_text_slice_length: int = 5

        return "{0} {1} {2} {3} {4} {5} {6}".format(
            self.__get_trimmed_and_justified_text__(
                identifier, identifier_name_slice_length, True
            ),
            self.__get_trimmed_and_justified_text__(
                distance, distance_text_slice_length
            ),
            self.__get_trimmed_and_justified_text__(speed, speed_text_slice_length),
            self.__get_trimmed_and_justified_text__(heading, bearing_slice_length),
            self.__get_trimmed_and_justified_text__(bearing, bearing_slice_length),
            self.__get_trimmed_and_justified_text__(
                altitude, altitude_text_slice_length
            ),
            self.__get_trimmed_and_justified_text__(
                delta, altitude_text_slice_length - 1
            ),
        )

    def __get_trimmed_and_justified_text__(
        self, text: str, max_length: int, isLeftJustified: bool = False
    ) -> str:
        truncated_string = text[:max_length]
        truncated_string = truncated_string.rstrip().lstrip()

        return (
            truncated_string.ljust(max_length)
            if isLeftJustified
            else truncated_string.rjust(max_length)
        )

    def __get_row_color__(self, index: int):
        return colors.YELLOW if index % 2 else colors.ORANGE


if __name__ == "__main__":
    from views.hud_elements import run_hud_element

    run_hud_element(AdsbTrafficListing)
