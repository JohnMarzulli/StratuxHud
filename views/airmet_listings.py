"""
View that shows the list of nearby traffic
"""

from typing import Dict

from data_sources.airports import load_example_flight_rules
from data_sources.textual_weather import (
    TextualReport,
    TextualWeatherClient,
    load_sample_text_reports,
)
from views.text_report_listings import TextReportListing


class AirmetListing(TextReportListing):
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

        self.__max_screen_lines__ += 1

    def __get_text_reports__(self) -> Dict[str, TextualReport]:
        return TextualWeatherClient.get_airmets()


if __name__ == "__main__":
    from data_sources.airports import load_example_airports
    from views.hud_elements import run_hud_element

    load_example_airports()
    load_sample_text_reports()
    load_example_flight_rules()

    run_hud_element(AirmetListing)
