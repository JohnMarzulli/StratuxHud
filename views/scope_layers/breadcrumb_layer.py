"""
Our own recent track on the scope.
"""

from core_services import breadcrumbs
from rendering import colors, drawing
from views.scope_layers.scope_frame import ScopeFrame
from views.scope_layers.scope_layer import ScopeLayer


class BreadcrumbLayer(ScopeLayer):
    """
    A green line along where we have been, fading with age, ending at
    our own aircraft.
    """

    def render(self, frame: ScopeFrame) -> None:
        breadcrumb_reports = breadcrumbs.INSTANCE.get_trail()
        breadcrumb_count = len(breadcrumb_reports)

        if not frame.has_position() or breadcrumb_count < 2:
            return

        current_heading = frame.orientation.get_precise_gps_heading()

        if current_heading is None or isinstance(current_heading, str):
            return

        line_width = self.canvas.line_width
        previous_position = None

        for index in range(breadcrumb_count - 1):
            proportion = breadcrumb_reports[index + 1][1]

            # If a point is skipped (too old or out of range) the line
            # must restart, or it would join across the gap.
            if proportion <= 0.0:
                previous_position = None
                continue

            coordinates = breadcrumb_reports[index][0]
            distance = frame.distance_to(coordinates)

            if not frame.is_in_range(distance):
                previous_position = None
                continue

            color = [int(component * proportion) for component in colors.GREEN]
            screen_coords = frame.project(frame.bearing_to(coordinates), distance)

            if previous_position is not None:
                drawing.renderer.segment(
                    frame.framebuffer,
                    color,
                    list(previous_position),
                    list(screen_coords),
                    width=line_width,
                )

            previous_position = screen_coords

        # Complete the line to our own aircraft.
        if previous_position is not None:
            drawing.renderer.segment(
                frame.framebuffer,
                list(colors.GREEN),
                list(previous_position),
                list(self.canvas.center),
                width=line_width,
            )
