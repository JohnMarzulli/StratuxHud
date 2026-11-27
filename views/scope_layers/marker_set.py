from views.scope_layers.scope_marker import ScopeMarker


from dataclasses import dataclass, field
from typing import List


@dataclass
class MarkerSet:
    detailed: List[ScopeMarker] = field(default_factory=list)
    simple: List[ScopeMarker] = field(default_factory=list)
