"""
View that shows the list of nearby traffic
"""

import datetime
from typing import Dict, List

from common_utils.text_pagination import get_consolidated_pages, get_wrapped_lines
from data_sources.ahrs_data import AhrsData
from data_sources.airports import AirportClient, load_example_flight_rules
from data_sources.textual_weather import TextualReport, load_sample_text_reports
from rendering import colors
from views.paginated_text_element import PaginatedTextElement
from views.text_line import TextLine


class TextReportListing(PaginatedTextElement):
    """
    View element that lists the closest frequencies.
    Lists airport, tower, approach, etc freqs.

    Implements a page/scroll view.
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

        self.__last_updated__ = None
        self.__reports_by_page__: List[List[TextLine]] = None

    def __get_text_reports__(self) -> Dict[str, TextualReport]:
        return {}

    def __get_text_pages__(self, orientation: AhrsData) -> List[List[TextLine]]:
        if (
            self.__reports_by_page__ is not None
            and self.__last_updated__ is not None
            and (
                datetime.datetime.now(datetime.timezone.utc) - self.__last_updated__
            ).total_seconds()
            < 60
        ):
            return self.__reports_by_page__

        reports_as_own_page = self.__get_reports_with_each_station_as_own_page__()
        self.__reports_by_page__ = get_consolidated_pages(
            reports_as_own_page,
            TextLine(colors.WHITE, " IDENT REPORT"),
            self.__max_screen_lines__,
        )

        self.__last_updated__ = datetime.datetime.now(datetime.timezone.utc)

        return self.__reports_by_page__

    def __get_reports_with_each_station_as_own_page__(self) -> List[List[TextLine]]:
        max_chars: int = self.__get_max_line_length__()

        reports: Dict[str, TextualReport] = self.__get_text_reports__()
        flight_rules = AirportClient.get_flight_rules()

        sorted_stations = sorted(reports.keys())

        lines: List[str] = []
        reports_as_own_page: List[List[TextLine]] = []

        for station in sorted_stations:
            known_flight_rules = (
                flight_rules[station] if station in flight_rules else "UNKNOWN"
            )

            color: List[int] = self.__get_flight_rule_color__(known_flight_rules)
            lines = get_wrapped_lines(reports[station].report, max_chars)
            justified_lines = self.__get_report_lines_with_station__(station, lines)
            report_lines = [
                TextLine(color, justified_text) for justified_text in justified_lines
            ]

            reports_as_own_page.append(report_lines)

        return reports_as_own_page

    def __get_report_lines_with_station__(
        self, station: str, report_lines: List[str]
    ) -> List[str]:
        station_text = station.rjust(6).ljust(6)
        justified_report_lines: List[str] = []

        for line in report_lines:
            justified_report_lines.append(f"{station_text} {line}")
            station_text = " " * len(station_text)

        return justified_report_lines

    def __get_flight_rule_color__(self, flight_rules):
        if flight_rules == "VFR":
            return colors.GREEN
        elif flight_rules == "MVFR":
            return colors.BLUE
        elif flight_rules == "IFR":
            return colors.RED
        elif flight_rules == "LIFR":
            return colors.MAGENTA

        return colors.WHITE


if __name__ == "__main__":
    from data_sources.airports import load_example_airports
    from views.hud_elements import run_hud_element

    load_example_airports()
    load_sample_text_reports()
    load_example_flight_rules()

    run_hud_element(TextReportListing)
