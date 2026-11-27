"""
View element for a weather "radar" that looks from the top downwards.
"""

from core_services.zoom_manager import DEFAULT_ZOOM_INDEX
from rendering import colors
from views.abstract_elements.top_down_scope import TopDownScope
from views.scope_layers import AirportLayer, WeatherLayer


class WeatherTopViewScope(TopDownScope):
    """
    A radar style scope showing NEXRAD weather and airports
    relative to our current position.

    White rings, manual zoom only, starting zoomed out to 20/50
    so there is more weather in view.
    """

    RING_COLOR = colors.WHITE
    ALLOWS_AUTOMATIC_ZOOM = False
    STARTING_ZOOM_INDEX = DEFAULT_ZOOM_INDEX + 3

    BACKGROUND_LAYERS = [WeatherLayer]
    FOREGROUND_LAYERS = [AirportLayer]


if __name__ == "__main__":
    from views.compass_and_heading_top_element import CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements
    from views.scope_layers.demo import auto_zooming, load_example_data

    load_example_data()

    run_hud_elements(
        [auto_zooming(WeatherTopViewScope), CompassAndHeadingTopElement, Groundspeed]
    )


# Orgeon FAA sample data should look like this:
#
#       111111111111111111
#    11122223333333333322211
#  111223333355555555533332211
# 11223333445555676555543333221
