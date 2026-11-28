"""
Which markers (traffic, airports) get their details drawn: the
identifier, altitude difference, and predicted path.

Everything else is drawn as just its symbol, which keeps the scope
readable when there is a lot nearby.

A rule SCORES each marker; higher means it deserves details more.
Each layer then gives details to its highest scoring markers that
are above its threshold, up to its cap (see the top of
traffic_layer.py and airport_layer.py):

    TRAFFIC_DETAIL_THRESHOLD = 0.0   Only scores above this qualify
    TRAFFIC_MAX_DETAILED = 20        At most this many get details

A rule is any function (a DetailFormula) taking the marker and the
frame and returning a number. By convention scores are 0.0 to 1.0,
and 0.0 means "never". True/False also work (as 1/0).

    def closest_ahead(marker, frame):
        if abs(frame.relative_angle(marker.bearing)) > 30.0:
            return 0.0
        return 1.0 / (1.0 + marker.distance)

    TRAFFIC_DETAIL_RULE = closest_ahead
    TRAFFIC_DETAIL_RULE = lambda marker, frame: 1.0 / (1.0 + marker.distance)
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
    marker.threat_level    Collision threat, 0 (none) to 3 (critical)

ThreatsFirst wraps any rule so collision threats always get details.
"""

from dataclasses import dataclass
from typing import Callable

from views.scope_layers.scope_frame import ScopeFrame
from views.scope_layers.scope_marker import ScopeMarker

# (marker, frame) -> score. Higher deserves details more; 0.0 means never.
DetailFormula = Callable[[ScopeMarker, ScopeFrame], float]


@dataclass(frozen=True)
class DetailRule:
    """
    Scores a marker by how close it is, from 1.0 (on top of us) down
    to 0.0 at max_distance_rings, so the cap keeps the nearest ones.

    Only markers ahead of us (within ahead_half_angle of our track),
    or within always_within_rings in any direction, score at all;
    everything else scores 0.0.

    Distances are in center-ring radii, so the rule scales with zoom:
    1.0 is the center ring, 0.5 is half way to it, 2.0 is the outer
    ring on the usual 1:2 ring ranges.

    Examples:
        DetailRule()                          Center ring; ahead, or within half of it
        DetailRule(ahead_half_angle=180.0)    Everything inside the center ring
        DetailRule(max_distance_rings=0.0)    Never show details
        DetailRule(ahead_half_angle=45.0)     A narrower "ahead" cone
        DetailRule(max_distance_rings=2.0)    Out to the outer ring
    """

    # Nothing beyond this distance gets details.
    max_distance_rings: float = 1.0
    # Degrees either side of our track that count as "ahead".
    # 90 is the whole front half; 180 is every direction.
    ahead_half_angle: float = 90.0
    # Closer than this, in any direction, always gets details.
    always_within_rings: float = 0.5

    def __call__(self, marker: ScopeMarker, frame: ScopeFrame) -> float:
        return self.score(marker, frame)

    def score(self, marker: ScopeMarker, frame: ScopeFrame) -> float:
        center_ring = frame.scope_range.center_ring_range
        max_distance = center_ring * self.max_distance_rings

        if max_distance <= 0.0 or marker.distance >= max_distance:
            return 0.0

        # 180 or more means every direction (directly behind folds to
        # -180, which a strict "<" would otherwise leave out).
        is_ahead = (
            self.ahead_half_angle >= 180.0
            or abs(frame.relative_angle(marker.bearing)) < self.ahead_half_angle
        )
        is_really_close = marker.distance < center_ring * self.always_within_rings

        if not (is_ahead or is_really_close):
            return 0.0

        return 1.0 - (marker.distance / max_distance)


@dataclass(frozen=True)
class ThreatsFirst:
    """
    Traffic that is a collision threat always gets details, ranked
    above everything else (worst first), wherever it is. Everything
    else is scored by the wrapped rule.

        ThreatsFirst(DetailRule(ahead_half_angle=45.0))
    """

    rule: DetailFormula = DetailRule()

    def __call__(self, marker: ScopeMarker, frame: ScopeFrame) -> float:
        if marker.threat_level > 0:
            # Above any 0..1 score, and higher for worse threats.
            return 1.0 + marker.threat_level

        return self.rule(marker, frame)
