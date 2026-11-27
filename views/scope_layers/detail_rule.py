"""
Which markers (traffic, airports) get their details drawn: the
identifier, altitude difference, and predicted path.

Everything else is drawn as just its symbol, which keeps the scope
readable when there is a lot nearby.

A rule is any function (a DetailFormula) that takes the marker and the
frame and answers True for "show details":

    def only_traffic_ahead(marker, frame):
        return abs(frame.relative_angle(marker.bearing)) < 30.0

    TRAFFIC_DETAIL_RULE = only_traffic_ahead
    TRAFFIC_DETAIL_RULE = lambda marker, frame: marker.distance < 2.0
    TRAFFIC_DETAIL_RULE = DetailRule(ahead_half_angle=45.0)

DetailRule is the standard formula with its numbers exposed. Useful
things a formula can read:

    marker.distance        Display units (what the rings are labeled in)
    marker.bearing         True degrees from us
    marker.label           Tail number / airport identifier
    frame.relative_angle(marker.bearing)   Degrees off our track, -180..180
    frame.scope_range.center_ring_range    Center ring, in display units
    frame.scope_range.max_ring_range       Outer ring, in display units
    frame.orientation      Our own AHRS/GPS data (altitude, speed, ...)
"""

from dataclasses import dataclass
from typing import Callable

from views.scope_layers.scope_frame import ScopeFrame
from views.scope_layers.scope_marker import ScopeMarker

# (marker, frame) -> True if the marker should get its details.
DetailFormula = Callable[[ScopeMarker, ScopeFrame], bool]


@dataclass(frozen=True)
class DetailRule:
    """
    A marker gets details when it is within max_distance_rings, and
    is either ahead of us (within ahead_half_angle of our track) or
    within always_within_rings in any direction.

    Distances are in center-ring radii, so the rule scales with zoom:
    1.0 is the center ring, 0.5 is half way to it, 2.0 is the outer
    ring on the usual 1:2 ring ranges.

    Examples:
        DetailRule()                          Center ring; ahead, or within half of it
        DetailRule(ahead_half_angle=180.0)    Everything inside the center ring
        DetailRule(max_distance_rings=0.0)    Never show details
        DetailRule(ahead_half_angle=45.0)     A narrower "ahead" cone
    """

    # Nothing beyond this distance gets details.
    max_distance_rings: float = 1.0
    # Degrees either side of our track that count as "ahead".
    # 90 is the whole front half; 180 is every direction.
    ahead_half_angle: float = 90.0
    # Closer than this, in any direction, always gets details.
    always_within_rings: float = 0.5

    def __call__(self, marker: ScopeMarker, frame: ScopeFrame) -> bool:
        return self.is_detail_worthy(marker, frame)

    def is_detail_worthy(self, marker: ScopeMarker, frame: ScopeFrame) -> bool:
        center_ring = frame.scope_range.center_ring_range

        if marker.distance > center_ring * self.max_distance_rings:
            return False

        # 180 or more means every direction (directly behind folds to
        # -180, which a strict "<" would otherwise leave out).
        is_ahead = (
            self.ahead_half_angle >= 180.0
            or abs(frame.relative_angle(marker.bearing)) < self.ahead_half_angle
        )
        is_really_close = marker.distance < center_ring * self.always_within_rings

        return is_ahead or is_really_close
