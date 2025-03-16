"""
View that shows the list of nearby traffic
"""

import pygame

from common_utils import geo_math, units
from data_sources.ahrs_data import NOT_AVAILABLE, AhrsData
from data_sources.airport_frequencies import AirportFrequency
from data_sources.airports import AirportClient
from rendering import colors
from views.adsb_element import AdsbElement


class AirportFrequencyListing(AdsbElement):
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

    def __get_listing__(self, report: list):
        name = report[0]
        dist = report[1]
        freq = report[2]
        freqType = report[3]
        remarks = report[4]

        # if self.__show_list__:
        return "{0} {1} {2} {3} {4}".format(
            self.__prepare_for_view__(name, self.__name_slice_length__, True),
            self.__prepare_for_view__(dist, self.__distance_text_slice_length__),
            self.__prepare_for_view__(freq, self.__freq_slice_length__),
            self.__prepare_for_view__(freqType, self.__freqType_slice_length__),
            self.__prepare_for_view__(remarks, self.__remarks_slice_length__),
        )

    def __prepare_for_view__(
        self, text: str, max_length: int, isLeftJustified: bool = False
    ) -> str:
        truncated_string = text[:max_length]
        truncated_string = truncated_string.rstrip().lstrip()

        return (
            truncated_string.ljust(max_length)
            if isLeftJustified
            else truncated_string.rjust(max_length)
        )

    def __get_padded_airport_freqs__(self, airport_freqs, orientation: AhrsData):
        pre_padded_text = self.__get_pre_padded_airport_freqs__(
            airport_freqs, orientation
        )

        if pre_padded_text is None:
            return []

        return [self.__get_listing__(report) for report in pre_padded_text]

    def __get_freq_text__(self, freq: AirportFrequency, orientation: AhrsData):
        # 'IDENT', 'NAME', 'DIST', 'FREQ', 'TYPE', 'REMARKS'
        distance_text = (
            self.__get_distance_string__(freq.distance, True)
            if orientation.gps_online
            else NOT_AVAILABLE
        )

        identToShow = (
            freq.facilityName if len(freq.facilityName) > 0 else freq.facilityId
        )

        return [
            identToShow,
            distance_text,
            freq.frequency,
            freq.frequencyName,
            freq.remarks,
        ]

    def __get_pre_padded_airport_freqs__(self, airport_freqs, orientation: AhrsData):

        # We do not want to show traffic on the ground.
        reports_to_show = []

        for ident in airport_freqs:
            for freq in airport_freqs[ident]:
                if (
                    freq.coordinates != None
                    and freq.coordinates[0] != None
                    and freq.coordinates[1] != None
                    and (len(freq.facilityName) > 0 or len(freq.facilityId) > 0)
                ):
                    freq.distance = (
                        geo_math.get_distance(orientation.position, freq.coordinates)
                        * units.yards_to_sm
                    )
                    reports_to_show.append(freq)

        report_count = len(reports_to_show)
        self.__page_count__ = int((report_count / self.__max_reports__) + 0.5)

        self.__page__ = min(self.__page_count__ - 1, self.__page__)
        self.__page__ = max(self.__page__, 0)
        slice_start = self.__page__ * self.__max_reports__

        # The __max_reports__ value is set based on the screen size
        # and how much can fit on the screen
        sorted_data = sorted(reports_to_show, key=lambda freq: freq.distance)
        reports_to_show = sorted_data[slice_start : slice_start + self.__max_reports__]

        pre_padded_text = [["NAME", "DIST", "FREQ", "TYPE", "REMARKS"]]

        pre_padded_text.extend(
            self.__get_freq_text__(freq, orientation) for freq in reports_to_show
        )
        return pre_padded_text

    def render(self, framebuffer, orientation: AhrsData):
        if (
            orientation is None
            or orientation.position is None
            or orientation.position[0] is None
            or orientation.position[1] is None
        ):
            return

        # Get the traffic, and bail out of we have none
        airport_frequencies = AirportClient.get_nearby_airport_frequencies()

        if airport_frequencies is None:
            return

        # Render a list of traffic that we have positions
        # for, along with the tail number

        y_pos = self.__listing_text_start_y__
        x_pos = self.__listing_text_start_x__

        padded_traffic_reports = self.__get_padded_airport_freqs__(
            airport_frequencies, orientation
        )

        index = 0
        for airport_freq in padded_traffic_reports:
            self.__render_text__(
                framebuffer,
                airport_freq,
                [x_pos, y_pos],
                self.__get_row_color__(index),
                self.__font_scale__,
            )

            y_pos += int(self.__next_line_distance__ * (self.__font_scale__ * 1.2))
            index += 1

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

    def __get_row_color__(self, index: int):
        if index == 0:
            return colors.WHITE

        return colors.YELLOW if index % 2 else colors.ORANGE


if __name__ == "__main__":
    from data_sources.airports import load_example_airports
    from views.hud_elements import run_hud_element

    load_example_airports()

    run_hud_element(AirportFrequencyListing)
