"""
Nearby airports on the scope.
"""

from typing import Dict

from common_utils.authoritative_time import get_system_time
from data_sources.airports import AirportClient
from rendering import colors
from views.scope_layers.marker_set import MarkerSet
from views.scope_layers.scope_marker import ScopeMarker
from views.scope_layers.detail_rule import DetailRule
from views.scope_layers.marker_layer import MarkerLayer
from views.scope_layers.scope_frame import ScopeFrame

# Which airports get their identifier.
# Any (marker, frame) -> bool function works here, for example:
#   AIRPORT_DETAIL_RULE = lambda marker, frame: marker.distance < 2.0
# See views/scope_layers/detail_rule.py for what a formula can use.
AIRPORT_DETAIL_RULE = DetailRule(
    max_distance_rings=1.0,  # Inside the center ring...
    ahead_half_angle=90.0,  # ...and ahead of us...
    always_within_rings=0.5,  # ...or within half the center ring.
)


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

    DETAIL_RULE = AIRPORT_DETAIL_RULE

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

        return self.split_by_detail(
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
