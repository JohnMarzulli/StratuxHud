"""
ADS-B traffic on the scope.
"""

from data_sources.data_cache import HudDataCache
from data_sources.traffic import Traffic
from rendering import colors
from views.scope_layers.marker_set import MarkerSet
from views.scope_layers.scope_marker import ScopeMarker
from views.scope_layers.marker_layer import (
    MarkerLayer,
    split_by_detail,
)
from views.scope_layers.scope_frame import ScopeFrame


class TrafficLayer(MarkerLayer):
    """
    Red arrows for airborne traffic, blue for traffic on the ground.
    Close traffic ahead also gets its identifier, altitude difference,
    and predicted path.
    """

    def get_markers(self, frame: ScopeFrame) -> MarkerSet:
        if not frame.orientation.gps_online:
            return MarkerSet()

        reports = [
            traffic
            for traffic in HudDataCache.get_reliable_traffic()
            if traffic.distance is not None
        ]

        # Furthest first, so closer traffic is drawn on top.
        reports.sort(key=lambda traffic: traffic.distance, reverse=True)

        return split_by_detail(
            [self.__to_marker__(frame, traffic) for traffic in reports], frame
        )

    def __to_marker__(self, frame: ScopeFrame, traffic: Traffic) -> ScopeMarker:
        distance_to_traffic = traffic.distance if traffic and traffic.distance is not None else 0.0

        return ScopeMarker(
            distance=frame.yards_to_display(distance_to_traffic),
            bearing=traffic.bearing if traffic.bearing is not None else 0.0,
            color=list(colors.BLUE if traffic.is_on_ground() else colors.RED),
            track=traffic.track,
            label=traffic.get_display_name(),
            sublabel=traffic.get_altitude_delta_text(frame.orientation),
            label_color=list(colors.YELLOW),
            prediction_points=traffic.get_prediction_points(),
        )
