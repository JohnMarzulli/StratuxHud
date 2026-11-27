"""
View element for a "radar scope" showing traffic over NEXRAD weather,
looking from the top downwards.
"""

from rendering import colors
from views.abstract_elements.top_down_scope import TopDownScope
from views.scope_layers import (
    AirportLayer,
    BreadcrumbLayer,
    TrafficLayer,
    WeatherLayer,
)


class AdsbAndWeatherScope(TopDownScope):
    """
    The traffic scope drawn over the weather scope: weather and our
    recent track under the rings, airports and traffic over them.

    Zooms like the traffic scope: green rings, auto-zoom by speed,
    manual zoom with up/down, and '7' returns to auto-zoom.
    """

    RING_COLOR = colors.GREEN
    ALLOWS_AUTOMATIC_ZOOM = True

    BACKGROUND_LAYERS = [WeatherLayer, BreadcrumbLayer]
    FOREGROUND_LAYERS = [AirportLayer, TrafficLayer]


if __name__ == "__main__":
    from views.compass_and_heading_top_element import CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements
    from views.scope_layers.demo import load_example_data

    load_example_data()

    run_hud_elements([AdsbAndWeatherScope, CompassAndHeadingTopElement, Groundspeed])
