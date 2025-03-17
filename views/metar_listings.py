"""
View that shows the list of nearby traffic
"""

import datetime
from typing import Dict, List

import pygame

from data_sources.ahrs_data import AhrsData
from data_sources.airports import AirportClient, load_example_flight_rules
from data_sources.textual_weather import (
    TextualReport,
    TextualWeatherClient,
    load_sample_text_reports,
)
from rendering import colors
from views.adsb_element import AdsbElement


class MetarLine(object):
    """
    Holds information need to render a METAR
    on the screen.

    This split helps with pagination and grouping.
    """

    def __init__(self, color: List[int], station: str, text: str):
        self.color = color

        self.station = station
        self.text = text


class MetarListing(AdsbElement):
    """
    View element that lists the closest frequencies.
    Lists airport, tower, approach, etc freqs.

    Implements a page/scroll view.
    """

    def uses_ahrs(self) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- False as this element does not use AHRS data.
        """

        return False

    def handle_events(self, unhandled_events) -> list:
        """
        Handle up/down events so scrolling can be implemented.

        Args:
            unhandled_events (_type_): Any events that have not yet been handeled.

        Returns:
            list: A list of events that were not handled by this code.
        """

        remaining_unhandled_events = []

        for event in unhandled_events:
            if event.type != pygame.KEYUP:
                continue

            if event.key in [pygame.K_UP, pygame.K_KP8]:
                self.__page__ -= 1
            elif event.key in [pygame.K_DOWN, pygame.K_KP2]:
                self.__page__ += 1
            else:
                remaining_unhandled_events.append(event)

        return remaining_unhandled_events

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

        self.__page__ = 0
        self.__listing_text_start_y__ = int(self.__font__.get_height())
        self.__listing_text_start_x__ = int(self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height())
        self.__font_scale__ = 0.6

        self.__max_screen_lines__ = (
            int(
                (self.__height__ - self.__listing_text_start_y__)
                / (self.__next_line_distance__ * self.__font_scale__)
            )
            - 3
        )

        self.__last_updated__ = None
        self.__reports_by_page__: List[List[MetarLine]] = None

    def render(self, framebuffer, orientation: AhrsData):
        reports_by_page = self.__get_metar_report_pages__()
        page_count = len(reports_by_page)

        self.__page__ = min(page_count - 1, self.__page__)
        self.__page__ = max(self.__page__, 0)

        # Render a list of traffic that we have positions
        # for, along with the tail number

        y_pos = self.__listing_text_start_y__
        x_pos = self.__listing_text_start_x__
        line_increment = int(self.__next_line_distance__ * (self.__font_scale__ * 1.2))

        report_start_x = x_pos + (self.__font_height__ * self.__font_scale__ * 4)

        if page_count > 0:
            report_page = reports_by_page[self.__page__]

            for report_line in report_page:
                self.__render_text__(
                    framebuffer,
                    report_line.station,
                    [x_pos, y_pos],
                    report_line.color,
                    self.__font_scale__,
                )

                self.__render_text__(
                    framebuffer,
                    report_line.text,
                    [report_start_x, y_pos],
                    report_line.color,
                    self.__font_scale__,
                )

                y_pos += line_increment

        self.__render_text__(
            framebuffer,
            f"Pg: {self.__page__ + 1} / {page_count}",
            [
                self.__left_border__,
                (self.__bottom_border__ - (self.__font_height__ << 1))
                + self.__font_height__,
            ],
            colors.YELLOW,
            0.5,
        )

    def __get_split_lines__(self, report: str, max_line_length: int) -> list[str]:
        tokens = report.split(" ")

        lines: List[str] = []
        current_line = ""

        while tokens:
            next_token: str = tokens[0]
            token_length = len(next_token)

            if len(current_line) + token_length > max_line_length:
                lines.append(current_line)
                current_line = next_token
            else:
                current_line += f" {next_token}"
                current_line = current_line.lstrip().rstrip()

            tokens = tokens[1:]

        if len(current_line) > 0:
            lines.append(current_line)

        return lines

    def __get_max_char_width__(self) -> int:
        report_start_x = self.__listing_text_start_x__ + (
            self.__font_height__ * self.__font_scale__ * 4
        )

        return int(
            (
                (((self.__center_x__ * 2) - report_start_x) / self.__font_scale__)
                / (self.__font_height__ / 2)
            )
            * 0.8
        )

    def __get_metar_report_pages__(self) -> List[List[MetarLine]]:
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
        self.__reports_by_page__ = self.__get_consolidated_report_pages__(
            reports_as_own_page
        )

        self.__last_updated__ = datetime.datetime.now(datetime.timezone.utc)

        return self.__reports_by_page__

    def __get_consolidated_report_pages__(
        self, reports_as_own_page: List[List[MetarLine]]
    ) -> List[List[MetarLine]]:
        consolidated_report_pages: List[List[MetarLine]] = []
        new_page: List[MetarLine] = []

        while reports_as_own_page:
            if len(new_page) + len(reports_as_own_page[0]) > self.__max_screen_lines__:
                consolidated_report_pages.append(new_page)
                new_page = []

            for line in reports_as_own_page[0]:
                new_page.append(line)

            reports_as_own_page = reports_as_own_page[1:]

        if len(new_page) > 0:
            consolidated_report_pages.append(new_page)

        return consolidated_report_pages

    def __get_reports_with_each_station_as_own_page__(self) -> List[List[MetarLine]]:
        max_chars: int = self.__get_max_char_width__()

        reports: Dict[str, TextualReport] = TextualWeatherClient.get_metars()
        flight_rules = AirportClient.get_flight_rules()

        # TODO - Experiment with sorting by name OR by distance
        sorted_stations = sorted(reports.keys())

        lines: List[str] = []
        reports_as_own_page: List[List[MetarLine]] = []

        for station in sorted_stations:
            known_flight_rules = (
                flight_rules[station] if station in flight_rules else "UNKNOWN"
            )

            color: List[int] = self.__get_flight_rule_color__(known_flight_rules)

            lines = self.__get_split_lines__(
                f"{station} {reports[station].report}", max_chars
            )

            station_text = station
            report_lines: List[MetarLine] = []

            for line in lines:
                report_lines.append(MetarLine(color, station_text, line))
                station_text = ""

            reports_as_own_page.append(report_lines)

        return reports_as_own_page

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

    run_hud_element(MetarListing)
