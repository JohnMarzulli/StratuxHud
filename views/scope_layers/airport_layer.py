"""
Nearby airports on the scope.
"""

from typing import Dict

from common_utils.authoritative_time import get_system_time
from data_sources.airports import AirportClient
from rendering import colors
from views.scope_layers.marker_set import MarkerSet
from views.scope_layers.scope_marker import ScopeMarker
from views.scope_layers.marker_layer import (
    MarkerLayer,
    split_by_detail,
)
from views.scope_layers.scope_frame import ScopeFrame


def get_airport_color(airport: Dict[str, any]):
    if "flightRules" not in airport:
        return colors.WHITE  # TODO - Find a way to determine if it has a tower

    flight_rules = airport["flightRules"]

    if flight_rules == "VFR":
        return colors.GREEN
    elif flight_rules == "MVFR":
        return colors.BLUE
    elif flight_rules == "IFR":
        return colors.RED
    elif flight_rules == "LIFR":
        return colors.MAGENTA

    return colors.GRAY


class AirportLayer(MarkerLayer):
    """
    A dot per airport, colored by flight rules. Close airports ahead
    also get their identifier. Blinks "EXPIRED" when the airport data
    is out of date.
    """

    def render(self, frame: ScopeFrame) -> None:
        if not AirportClient.is_airport_data_valid() and get_system_time().second % 2 == 0:
            canvas = self.canvas
            canvas.draw_right_justified_text(
                frame.framebuffer,
                "EXPIRED",
                [canvas.right_border, canvas.bottom_border - canvas.font_height],
                colors.RED,
            )

        super().render(frame)

    def get_markers(self, frame: ScopeFrame) -> MarkerSet:
        if frame.orientation is None or not frame.has_position():
            return MarkerSet()

        nearby_airports = AirportClient.get_nearby_airports()

        return split_by_detail(
            [
                self.__to_marker__(frame, nearby_airports[airport_id])
                for airport_id in nearby_airports
            ],
            frame,
        )

    def __to_marker__(self, frame: ScopeFrame, airport: Dict[str, any]) -> ScopeMarker:
        # Airport data format:
        # {"coordinates":{"longitude":-122.149561389,"latitude":47.280656111},"ident":"WA84","name":"Auburn Academy","airportType":"AD","isPublic":false}
        coordinates = [
            airport["coordinates"]["latitude"],
            airport["coordinates"]["longitude"],
        ]

        return ScopeMarker(
            distance=frame.distance_to(coordinates),
            bearing=frame.bearing_to(coordinates),
            color=get_airport_color(airport),
            label=airport["ident"],
        )
