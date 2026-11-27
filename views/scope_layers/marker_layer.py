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

import inspect
from typing import List, Optional

import pygame

from rendering import colors, drawing
from views.scope_layers.detail_rule import DetailFormula, DetailRule
from views.scope_layers.marker_set import MarkerSet
from views.scope_layers.scope_marker import ScopeMarker
from views.scope_layers.scope_frame import ScopeFrame
from views.scope_layers.scope_layer import ScopeLayer

# A rim around every marker symbol so red traffic still stands out
# over red/orange weather. Set the color to None to turn it off.
MARKER_OUTLINE_COLOR = colors.GRAY
# Width of the visible rim, as a multiple of the scope's thin line width.
MARKER_OUTLINE_WIDTH = 2


def is_drawable(marker: ScopeMarker, frame: ScopeFrame) -> bool:
    """
    Will the marker actually be drawn: inside the outer ring and on screen?
    """
    if marker.distance is None or not frame.is_in_range(marker.distance):
        return False

    return frame.is_on_screen(*frame.project(marker.bearing, marker.distance))


def split_by_detail(
    markers: List[ScopeMarker],
    frame: ScopeFrame,
    rule: DetailFormula,
    threshold: float = 0.0,
    max_detailed: Optional[int] = None,
) -> MarkerSet:
    """
    Scores every drawable marker with the rule, and gives details to
    the highest scoring ones above the threshold, up to max_detailed
    (None for no limit). Ties go to the marker supplied first.

    Both lists keep the order the markers were supplied in, since that
    is the order they are drawn in.
    """
    scores = {}

    for index, marker in enumerate(markers):
        if is_drawable(marker, frame):
            score = rule(marker, frame)

            if score is not None and score > threshold:
                scores[index] = score

    # sorted() is stable, so equal scores keep their supplied order.
    ranked = sorted(scores, key=lambda index: scores[index], reverse=True)
    chosen = set(ranked if max_detailed is None else ranked[: max(0, max_detailed)])

    marker_set = MarkerSet()

    for index, marker in enumerate(markers):
        if index in chosen:
            marker_set.detailed.append(marker)
        else:
            marker_set.simple.append(marker)

    return marker_set


class MarkerLayer(ScopeLayer):
    """
    Draws the markers a subclass supplies.

    Which markers get labels:
        DETAIL_RULE       Scores each marker. Any DetailFormula: a
                          DetailRule, a function, or a lambda taking
                          (marker, frame).
        DETAIL_THRESHOLD  Only scores above this qualify.
        MAX_DETAILED      At most this many, highest scores first
                          (None for no limit).
    Each layer type sets its own, and any of them can be replaced on a
    subclass or a single instance.

    Simple markers are drawn first, then detailed ones, so the
    markers that matter most end up on top. Within each list markers
    are drawn in the order given.
    """

    DETAIL_RULE: DetailFormula = DetailRule()
    DETAIL_THRESHOLD: float = 0.0
    MAX_DETAILED: Optional[int] = None

    def get_markers(self, frame: ScopeFrame) -> MarkerSet:
        raise NotImplementedError

    def split_by_detail(self, markers: List[ScopeMarker], frame: ScopeFrame) -> MarkerSet:
        """
        Sorts markers into detailed and simple using this layer's
        DETAIL_RULE, DETAIL_THRESHOLD, and MAX_DETAILED.
        """
        return split_by_detail(
            markers,
            frame,
            self.__get_detail_rule__(),
            self.DETAIL_THRESHOLD,
            self.MAX_DETAILED,
        )

    def __get_detail_rule__(self) -> DetailFormula:
        """
        The rule, as written. A plain function or lambda stored on the
        class would otherwise be bound as a method and handed this
        layer as its "marker".
        """
        rule = inspect.getattr_static(self, "DETAIL_RULE")

        return rule.__func__ if isinstance(rule, staticmethod) else rule

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
