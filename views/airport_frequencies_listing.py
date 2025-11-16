"""
View that shows the list of nearby traffic
"""

from typing import List

from common_utils import geo_math, units
from common_utils.text_pagination import (
    get_lines_grouped_by_page,
    get_trimmed_and_justified_text,
)
from data_sources.ahrs_data import NOT_AVAILABLE, AhrsData
from data_sources.airport_frequencies import AirportFrequency
from data_sources.airports import AirportClient
from rendering import colors
from views.abstract_elements.paginated_text_element import PaginatedTextElement
from views.abstract_elements.text_line import TextLine


class AirportFrequencyListing(PaginatedTextElement):
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

    def __get_text_pages__(self, orientation: AhrsData) -> List[List[TextLine]]:
        airport_frequencies = AirportClient.get_nearby_airport_frequencies()

        if airport_frequencies is None:
            return []

        all_frequencies: List[str] = self.__get_all_frequency_lines__(
            airport_frequencies, orientation
        )

        return get_lines_grouped_by_page(
            all_frequencies, self.__get_page_header__(), self.__max_screen_lines__
        )

    def __get_all_frequency_lines__(
        self, airport_freqs, orientation: AhrsData
    ) -> List[TextLine]:
        unsorted_freqs = []
        index: int = 0
        text_lines: List[TextLine] = []

        for ident in airport_freqs:
            for freq in airport_freqs[ident]:
                if freq.facilityType == "NAVAID":
                    continue

                freq_as_number = float(freq.frequency)

                if (freq_as_number < 100) or (freq_as_number > 140):
                    continue

                if (
                    orientation.position != None
                    and orientation.position[0] != None
                    and orientation.position[1] != None
                    and freq.coordinates != None
                    and freq.coordinates[0] != None
                    and freq.coordinates[1] != None
                    and (len(freq.facilityName) > 0 or len(freq.facilityId) > 0)
                ):
                    freq.distance = (
                        geo_math.get_distance(orientation.position, freq.coordinates)
                        * units.yards_to_sm
                    )
                    unsorted_freqs.append(freq)

        sorted_freqs = sorted(unsorted_freqs, key=lambda freq: freq.distance)

        for freq in sorted_freqs:
            text_lines.append(
                TextLine(
                    self.__get_row_color__(index),
                    self.__get_freq_text__(freq, orientation),
                )
            )
            index += 1

        return text_lines

    def __get_page_header__(self) -> TextLine:
        return TextLine(
            colors.WHITE,
            self.__get_justified_line__("NAME", "DIST", "   FREQ", "TYPE", "Remarks"),
        )

    def __get_freq_text__(self, freq: AirportFrequency, orientation: AhrsData) -> str:
        # 'IDENT', 'NAME', 'DIST', 'FREQ', 'TYPE', 'REMARKS'
        distance_text = (
            self.__get_distance_string_without_units__(freq.distance)
            if orientation.gps_online
            else NOT_AVAILABLE
        )

        identToShow = (
            freq.facilityName if len(freq.facilityName) > 0 else freq.facilityId
        )

        return self.__get_justified_line__(
            identToShow,
            distance_text,
            freq.frequency.ljust(7),
            freq.frequencyName,
            freq.remarks,
        )

    def __get_justified_line__(
        self, name: str, distance: str, frequency: str, freq_type: str, remarks: str
    ):
        name_slice_length: int = 15
        distance_text_slice_length: int = 6
        freqType_slice_length: int = 8
        remarks_slice_length: int = 15

        return "{0} {1} {2} {3} {4}".format(
            get_trimmed_and_justified_text(name, name_slice_length, True),
            get_trimmed_and_justified_text(distance, distance_text_slice_length),
            frequency,
            get_trimmed_and_justified_text(freq_type, freqType_slice_length),
            get_trimmed_and_justified_text(remarks, remarks_slice_length),
        )

    def __get_row_color__(self, index: int):
        return colors.YELLOW if index % 2 else colors.ORANGE


if __name__ == "__main__":
    from data_sources.airports import load_example_airports
    from views.hud_elements import run_hud_element

    load_example_airports()

    run_hud_element(AirportFrequencyListing)
