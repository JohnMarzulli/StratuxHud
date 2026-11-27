"""
Shared geometry for the top-down scope layers.

ScopeCanvas: what never changes for a scope (where it is on screen,
             line widths, how to draw text).
ScopeFrame:  what changes every frame (the framebuffer, our position
             and heading, the zoom range, the display units) plus the
             math to put things on screen.

Distances
---------
Everything a layer compares to the zoom range must be in DISPLAY
units (statute miles, nautical miles, or kilometers, whatever the
user chose), because that is what the range rings are labeled in.
The data comes in two other units:

    * ADS-B traffic distances are raw YARDS -> yards_to_display()
    * geo_math distances are STATUTE MILES  -> statute_to_display()
"""

import math
from typing import Tuple

from common_utils import fast_math, geo_math, units
from core_services.scope_range import ScopeRange
from data_sources.ahrs_data import AhrsData
from views.scope_layers.scope_canvas import ScopeCanvas

# Rotates a true bearing so 0 (straight ahead) points up the screen.
TRAFFIC_PHASE_SHIFT = -90


class ScopeFrame:
    """
    Everything a layer needs to draw one frame.
    """

    def __init__(
        self,
        canvas: ScopeCanvas,
        framebuffer,
        orientation: AhrsData,
        scope_range: ScopeRange,
        display_units: str,
    ) -> None:
        self.canvas = canvas
        self.framebuffer = framebuffer
        self.orientation = orientation
        self.scope_range = scope_range
        self.display_units = display_units
        self.heading: float = orientation.get_precise_gps_heading()

    # -- Units ----------------------------------------------------------

    def yards_to_display(self, yards: float) -> float:
        return units.get_converted_units(self.display_units, yards)

    def statute_to_display(self, statute_miles: float) -> float:
        return self.yards_to_display(statute_miles * units.yards_to_sm)

    def display_to_statute(self, display_distance: float) -> float:
        # Converting one statute mile gives "display units per statute mile".
        return display_distance / self.statute_to_display(1.0)

    # -- Position -------------------------------------------------------

    def has_position(self) -> bool:
        position = self.orientation.position

        return (
            position is not None
            and position[0] is not None
            and position[1] is not None
        )

    def distance_to(self, coordinates) -> float:
        """
        Display-unit distance from us to [lat, lon].
        """
        return self.statute_to_display(
            geo_math.get_distance(self.orientation.position, coordinates)
        )

    def bearing_to(self, coordinates) -> float:
        return geo_math.get_bearing(self.orientation.position, coordinates)

    # -- Projection -----------------------------------------------------

    def pixel_distance(self, display_distance: float) -> int:
        proportion = display_distance / self.scope_range.max_ring_range

        return int(self.canvas.max_pixel_radius * proportion)

    def project_angle(
        self, screen_angle: float, pixel_distance: float
    ) -> Tuple[int, int]:
        """
        Screen position at an angle (0 = right, 90 = down) and a
        number of pixels from the scope center.
        """
        radians = math.radians(screen_angle)

        return (
            int((math.cos(radians) * pixel_distance) + self.canvas.center[0]),
            int((math.sin(radians) * pixel_distance) + self.canvas.center[1]),
        )

    def project(self, bearing: float, display_distance: float) -> Tuple[int, int]:
        """
        Screen position of something at a true bearing and display
        distance from us, rotated so our track points up.
        """
        angle = fast_math.wrap_degrees(
            TRAFFIC_PHASE_SHIFT + (bearing - self.heading)
        )

        return self.project_angle(angle, self.pixel_distance(display_distance))

    def project_position(self, coordinates) -> Tuple[int, int]:
        """
        Screen position of [lat, lon].
        """
        return self.project(self.bearing_to(coordinates), self.distance_to(coordinates))

    def is_on_screen(self, screen_x: float, screen_y: float) -> bool:
        return 0 <= screen_x <= self.canvas.width and 0 <= screen_y <= self.canvas.height

    def is_in_range(self, display_distance: float) -> bool:
        return display_distance <= self.scope_range.max_ring_range

    def relative_angle(self, bearing: float) -> float:
        """
        How far a bearing is from our track, folded into [-180, 180)
        so something just across north counts as nearly ahead.
        """
        return ((bearing - self.heading + 180.0) % 360.0) - 180.0
