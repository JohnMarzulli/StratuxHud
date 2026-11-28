"""
Drawable layers for the top-down scopes.

Every layer has the same interface (see ScopeLayer), so a scope is
just a list of layers drawn under and over its range rings:

    WeatherLayer     NEXRAD reflectivity
    BreadcrumbLayer  Where we have been
    AirportLayer     Nearby airports (a MarkerLayer)
    TrafficLayer     ADS-B traffic (a MarkerLayer)
"""

from views.scope_layers.detail_rule import DetailRule, ThreatsFirst
from views.scope_layers.marker_set import MarkerSet
from views.scope_layers.scope_canvas import ScopeCanvas
from views.scope_layers.scope_marker import ScopeMarker
from views.scope_layers.airport_layer import AirportLayer
from views.scope_layers.breadcrumb_layer import BreadcrumbLayer
from views.scope_layers.marker_layer import MarkerLayer
from views.scope_layers.scope_frame import ScopeFrame
from views.scope_layers.scope_layer import ScopeLayer
from views.scope_layers.traffic_layer import TrafficLayer
from views.scope_layers.weather_layer import WeatherLayer

__all__ = [
    "AirportLayer",
    "BreadcrumbLayer",
    "DetailRule",
    "MarkerLayer",
    "MarkerSet",
    "ScopeCanvas",
    "ScopeFrame",
    "ScopeLayer",
    "ScopeMarker",
    "ThreatsFirst",
    "TrafficLayer",
    "WeatherLayer",
]
