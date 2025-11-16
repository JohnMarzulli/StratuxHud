"""
View that shows the list of nearby traffic

Recommended view:

{
    "elements": [
    "TAF Listing",
    "Traffic Not Available",
    "GPS Not Available"
    ],
    "name": "TAFS"
}
"""

from typing import Dict, List

from common_utils.text_pagination import get_wrapped_lines
from core_services import weather_report_classification
from data_sources.airports import load_example_flight_rules
from data_sources.textual_weather import (
    TextualReport,
    TextualWeatherClient,
    load_sample_text_reports,
)
from views.abstract_elements.text_line import TextLine
from views.abstract_elements.text_report_listings import TextReportListing


class TafListing(TextReportListing):
    """
    View element that lists the closest frequencies.
    Lists airport, tower, approach, etc freqs.

    Implements a page/scroll view.
    """

    def __get_text_reports__(self) -> Dict[str, TextualReport]:
        return TextualWeatherClient.get_tafs()

    def __get_reports_with_each_station_as_own_page__(self) -> List[List[TextLine]]:
        """
        Overload of report page generation that colors each line
        with the anticipated color of the TAF during a given
        timeframe

        Returns:
            List[List[TextLine]]: A list of pages, with each page containing a single TAF
        """
        max_chars: int = self.__get_max_line_length__()

        reports: Dict[str, TextualReport] = self.__get_text_reports__()
        sorted_stations = sorted(reports.keys())

        lines: List[str] = []
        reports_as_own_page: List[List[TextLine]] = []

        for station in sorted_stations:
            lines = get_wrapped_lines(reports[station].report, max_chars)
            justified_lines = self.__get_report_lines_with_station__(station, lines)
            previous_flight_rules = weather_report_classification.INVALID

            report_lines: List[TextLine] = []

            for justified_line in justified_lines:
                new_flight_rule = weather_report_classification.get_category(
                    justified_line
                )
                if new_flight_rule == weather_report_classification.INVALID:
                    new_flight_rule = previous_flight_rules

                report_lines.append(
                    TextLine(
                        self.__get_flight_rule_color__(new_flight_rule), justified_line
                    )
                )

            reports_as_own_page.append(report_lines)

        return reports_as_own_page


if __name__ == "__main__":
    from data_sources.airports import load_example_airports
    from views.hud_elements import run_hud_element

    load_example_airports()
    load_sample_text_reports()
    load_example_flight_rules()

    run_hud_element(TafListing)

    # EXAMPLE TAF
    # First sectionds are VFR
    # Final section is MVFR (FM200300 which is 8PM PDT)
    # 190540Z 1906/2006 17004KT P6SM BKN045 OVC090
    # FM191100 13003KT P6SM OVC060
    # FM191800 14004KT P6SM -RA OVC050
    # FM192200 13010G20KT P6SM -RA OVC040
    # FM200300 15012G25KT P6SM -RA OVC030
