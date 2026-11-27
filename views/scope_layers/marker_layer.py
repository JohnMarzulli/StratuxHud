"""
Point-like things on the scope (traffic, airports) described as
markers, and one layer that knows how to draw them all.

A source only says WHAT to draw:

    get_markers(frame) -> MarkerSet(detailed=[...], simple=[...])

    detailed: symbol + label + sublabel + prediction line
    simple:   just the symbol (an arrow if it has a track, else a dot)

and MarkerLayer does the drawing, culling, and layout the same way
for every source.
"""

from typing import List

import pygame

from rendering import colors, drawing
from views.scope_layers.marker_set import MarkerSet
from views.scope_layers.scope_marker import ScopeMarker
from views.scope_layers.scope_frame import ScopeFrame
from views.scope_layers.scope_layer import ScopeLayer

# A rim around every marker symbol so red traffic still stands out
# over red/orange weather. Set the color to None to turn it off.
MARKER_OUTLINE_COLOR = colors.GRAY
# Width of the visible rim, as a multiple of the scope's thin line width.
MARKER_OUTLINE_WIDTH = 2


def is_detail_worthy(marker: ScopeMarker, frame: ScopeFrame) -> bool:
    """
    The clutter rule both traffic and airports use: only things inside
    the center ring get details, and of those only things ahead of us
    (within 90 degrees of our track) or really close.
    """
    center_ring = frame.scope_range.center_ring_range

    if marker.distance > center_ring:
        return False

    is_ahead = abs(frame.relative_angle(marker.bearing)) < 90.0
    is_really_close = marker.distance < (center_ring / 2.0)

    return is_ahead or is_really_close


def split_by_detail(markers: List[ScopeMarker], frame: ScopeFrame) -> MarkerSet:
    """
    Sorts markers into detailed and simple using is_detail_worthy,
    keeping their order.
    """
    marker_set = MarkerSet()

    for marker in markers:
        if is_detail_worthy(marker, frame):
            marker_set.detailed.append(marker)
        else:
            marker_set.simple.append(marker)

    return marker_set


class MarkerLayer(ScopeLayer):
    """
    Draws the markers a subclass supplies.

    Simple markers are drawn first, then detailed ones, so the
    markers that matter most end up on top. Within each list markers
    are drawn in the order given.
    """

    def get_markers(self, frame: ScopeFrame) -> MarkerSet:
        raise NotImplementedError

    def render(self, frame: ScopeFrame) -> None:
        marker_set = self.get_markers(frame)

        for marker in marker_set.simple:
            self.__draw_marker__(frame, marker, False)

        for marker in marker_set.detailed:
            self.__draw_marker__(frame, marker, True)

    def __draw_marker__(
        self, frame: ScopeFrame, marker: ScopeMarker, is_detailed: bool
    ) -> None:
        if marker.distance is None or not frame.is_in_range(marker.distance):
            return

        screen_x, screen_y = frame.project(marker.bearing, marker.distance)

        if not frame.is_on_screen(screen_x, screen_y):
            return

        position = (screen_x, screen_y)

        if is_detailed and marker.prediction_points:
            self.__draw_prediction__(frame, marker, position)

        self.__draw_symbol__(frame, marker, position)

        if is_detailed and self.canvas.draw_identifiers:
            self.__draw_labels__(frame, marker, position)

    def __draw_symbol__(self, frame: ScopeFrame, marker: ScopeMarker, position):
        canvas = self.canvas
        outline_width = max(1, int(canvas.thin_line_width * MARKER_OUTLINE_WIDTH))
        has_outline = MARKER_OUTLINE_COLOR is not None

        # The outline goes down first and the symbol is filled over
        # it, so only the rim outside the symbol shows.
        if marker.track is not None:
            points = canvas.get_traffic_indicator(
                list(position), frame.heading, marker.track
            )

            if has_outline:
                drawing.renderer.segments(
                    frame.framebuffer,
                    list(MARKER_OUTLINE_COLOR),
                    True,
                    points,
                    outline_width << 1,  # Centered on the edge; half shows
                    False,
                )

            drawing.renderer.polygon(
                frame.framebuffer,
                marker.color,
                points,
                not canvas.reduced_visuals,
            )
        else:
            if has_outline:
                drawing.renderer.filled_circle(
                    frame.framebuffer,
                    list(MARKER_OUTLINE_COLOR),
                    list(position),
                    canvas.no_direction_target_size + outline_width,
                    False,
                )

            drawing.renderer.filled_circle(
                frame.framebuffer,
                marker.color,
                list(position),
                canvas.no_direction_target_size,
                not canvas.reduced_visuals,
            )

    def __draw_labels__(self, frame: ScopeFrame, marker: ScopeMarker, position):
        canvas = self.canvas
        label_color = list(marker.label_color or marker.color)
        label_y = position[1] + (canvas.no_direction_target_size << 2)

        for text in (marker.label, marker.sublabel):
            if text is not None:
                canvas.draw_centered_text(
                    frame.framebuffer,
                    text,
                    [position[0], label_y],
                    label_color,
                    list(colors.BLACK),
                    0.5,
                )

            label_y += canvas.font_half_height

    def __draw_prediction__(self, frame: ScopeFrame, marker: ScopeMarker, position):
        """
        Draws the predicted path as line segments, starting at the
        marker. Invalid points (None) break the path.
        """
        points = marker.prediction_points

        if not points:
            return

        if len(points) < 2:
            return

        positions = [position if points[0] is not None else None]
        positions.extend(
            None if point is None else frame.project_position([point[0], point[1]])
            for point in points[1:]
        )
        screen = pygame.Rect(0, 0, self.canvas.width, self.canvas.height)
        width = max(2, self.canvas.line_width)

        for start, end in zip(positions, positions[1:]):
            if start is None or end is None:
                continue

            segment = screen.clipline(start, end)

            if segment:
                drawing.renderer.segment(
                    frame.framebuffer,
                    marker.color,
                    list(segment[0]),
                    list(segment[1]),
                    width=width,
                )
