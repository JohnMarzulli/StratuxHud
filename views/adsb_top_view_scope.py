"""
View element for a "radar scope" of traffic that looks from the top downwards.
"""

from rendering import colors
from views.abstract_elements.top_down_scope import TopDownScope
from views.scope_layers import AirportLayer, BreadcrumbLayer, TrafficLayer


class AdsbTopViewScope(TopDownScope):
    """
    A radar style scope showing where traffic and airports are
    relative to our current position, with our recent track.

    Green rings, auto-zoom by speed, and '7' returns to auto-zoom.
    """

    RING_COLOR = colors.GREEN
    ALLOWS_AUTOMATIC_ZOOM = True

    BACKGROUND_LAYERS = [BreadcrumbLayer]
    FOREGROUND_LAYERS = [AirportLayer, TrafficLayer]


if __name__ == "__main__":
    from views.compass_and_heading_top_element import CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements

    run_hud_elements([AdsbTopViewScope, CompassAndHeadingTopElement, Groundspeed])
