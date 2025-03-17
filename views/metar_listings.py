"""
View that shows the list of nearby traffic
"""

from typing import Dict, List

import pygame

from common_utils import geo_math, units
from data_sources.ahrs_data import NOT_AVAILABLE, AhrsData
from data_sources.airport_frequencies import AirportFrequency
from data_sources.airports import AirportClient, load_example_flight_rules
from data_sources.textual_weather import (
    TextualReport,
    TextualWeatherClient,
    load_sample_text_reports,
)
from rendering import colors
from views.adsb_element import AdsbElement


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
        self.__page_count__ = 0
        self.__listing_text_start_y__ = int(self.__font__.get_height())
        self.__listing_text_start_x__ = int(self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height())

        self.__name_slice_length__ = 15
        self.__distance_text_slice_length__ = 8
        self.__freq_slice_length__ = 7
        self.__freqType_slice_length__ = 8
        self.__remarks_slice_length__ = 12
        self.__font_scale__ = 0.6

        self.__max_reports__ = (
            int(
                (self.__height__ - self.__listing_text_start_y__)
                / (self.__next_line_distance__ * self.__font_scale__ * 1.2)
            )
            - 3
        )

    def render(self, framebuffer, orientation: AhrsData):
        self.__page__ = min(self.__page_count__ - 1, self.__page__)
        self.__page__ = max(self.__page__, 0)

        # TODO - Remove this
        self.__page_count__ = 1

        reports: Dict[str, TextualReport] = TextualWeatherClient.get_metars()
        flight_rules = AirportClient.get_flight_rules()

        # Render a list of traffic that we have positions
        # for, along with the tail number

        y_pos = self.__listing_text_start_y__
        x_pos = self.__listing_text_start_x__

        max_lines = 12

        line_increment = int(self.__next_line_distance__ * (self.__font_scale__ * 1.2))

        report_start_x = x_pos + (self.__font_height__ * self.__font_scale__ * 4)

        max_chars = int(
            (
                (((self.__center_x__ * 2) - report_start_x) / self.__font_scale__)
                / (self.__font_height__ / 2)
            )
            * 0.8
        )

        # TODO - Experiment with sorting by name OR by distance
        sorted_stations = sorted(reports.keys())

        lines_shown = 0

        # TODO - Split this up into an array of arrays. The top level is the page.
        # TODO - Maybe the sublist contains a tuple of the color AND the text?

        for station in sorted_stations:
            known_flight_rules = (
                flight_rules[station] if station in flight_rules else "UNKNOWN"
            )

            lines = self.__get_split_lines__(
                f"{station} {reports[station].report}", max_chars
            )

            if (lines_shown + len(lines)) > max_lines:
                break

            self.__render_text__(
                framebuffer,
                station,
                [x_pos, y_pos],
                self.__get_flight_rule_color__(known_flight_rules),
                self.__font_scale__,
            )

            for line in lines:
                self.__render_text__(
                    framebuffer,
                    line,
                    [report_start_x, y_pos],
                    self.__get_flight_rule_color__(known_flight_rules),
                    self.__font_scale__,
                )

                y_pos += line_increment

            lines_shown += len(lines)

        self.__render_text__(
            framebuffer,
            f"Pg: {self.__page__ + 1} / {self.__page_count__}",
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

        while len(tokens) > 0:
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

    def __get_row_color__(self, index: int):
        if index == 0:
            return colors.WHITE

        return colors.YELLOW if index % 2 else colors.ORANGE


if __name__ == "__main__":
    from data_sources.airports import load_example_airports
    from views.hud_elements import run_hud_element

    load_example_airports()
    load_sample_text_reports()
    load_example_flight_rules()

    run_hud_element(MetarListing)
