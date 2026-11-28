from dataclasses import dataclass
from typing import Optional


@dataclass
class ScopeMarker:
    distance: float  # Display units (what the rings are labeled in)
    bearing: float  # True degrees from us
    color: list
    track: Optional[float] = None  # Arrow when set, dot when None
    label: Optional[str] = None  # Tail number / airport identifier
    sublabel: Optional[str] = None  # Altitude delta (traffic)
    label_color: Optional[list] = None  # Defaults to color
    # [(lat, lon, alt) | None, ...]; the first point is the marker itself.
    prediction_points: Optional[list] = None
    # How much of a collision hazard it is (a traffic_threat.ThreatLevel);
    # 0 is none, and is what everything that isn't traffic uses.
    threat_level: int = 0
