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
import math
from dataclasses import dataclass
from typing import List, Optional

import pygame

from common_utils.authoritative_time import get_system_time
from core_services.traffic_threat import ThreatLevel
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


@dataclass(frozen=True)
class ThreatStyle:
    """
    How a marker is drawn at one threat level.
    """

    # Rim color; None for no rim.
    outline_color: Optional[tuple]
    # Rim width, as a multiple of MARKER_OUTLINE_WIDTH.
    outline_width: float = 1.0
    # Symbol size, as a multiple of its normal size.
    scale: float = 1.0
    # Blinks per second, 0 for none. For the second half of each
    # blink the whole symbol and its rim are dropped, leaving only a
    # hairline outline (blink_outline_width) so it can still be found.
    flash_hz: float = 0.0
    # Width of that hairline, as a multiple of the scope's thin line
    # width; 0 makes the symbol vanish completely.
    blink_outline_width: float = 1.0
    # Pulses per second, 0 for none. A pulse grows the symbol by up to
    # pulse_scale (on top of scale) and back again.
    pulse_hz: float = 0.0
    pulse_scale: float = 0.0
    # At the peak of each pulse a ring leaves the symbol, expanding to
    # ring_scale times the symbol's normal size as it fades out. It is
    # drawn through blinks. 0 for no ring.
    ring_scale: float = 0.0
    # Width of the ring, as a multiple of the scope's thin line width.
    ring_width: float = 2.0


# How traffic looks at each traffic_threat.ThreatLevel. Level NONE,
# and everything that isn't traffic, keeps the plain
# MARKER_OUTLINE_COLOR rim.
THREAT_STYLES = {
    ThreatLevel.WARNING: ThreatStyle(colors.YELLOW),
    ThreatLevel.ALERT: ThreatStyle(colors.RED, scale=1.5, flash_hz=4.0),
    ThreatLevel.CRITICAL: ThreatStyle(
        colors.RED, scale=1.5, flash_hz=4.0,
        pulse_hz=1.5, pulse_scale=1.0, ring_scale=5.0,
    ),
}


# How far a rim's corner may reach past the symbol's corner, as a
# multiple of the rim width, before it is cut flat. Keeps the narrow
# tip of the traffic arrow from growing a long spike.
OUTLINE_MITER_LIMIT = 2.0
# An arrow's rim is pushed out by this fraction of the outline width.
# Matches the weight of the rim before it was drawn as a polygon (as
# thick lines centered on the edges, so about half showed).
ARROW_OUTLINE_FRACTION = 0.5
# Extra pixels pushed out beyond that. Filling rounds corner positions
# down to whole pixels and the symbol's smoothed edge covers another,
# which would otherwise leave some edges with almost no rim depending
# on which way the arrow points.
OUTLINE_PIXEL_ALLOWANCE = 1.0


def get_outline_polygon(points: list, width: float, miter_limit: float = OUTLINE_MITER_LIMIT) -> list:
    """
    The points of a convex polygon pushed out by width on every side,
    for drawing a solid rim behind it with no gaps at the corners.

    Each corner is where its two pushed-out edges meet, unless that is
    more than miter_limit * width from the original corner; then the
    spike is cut off square, miter_limit * width beyond the corner, so
    a sharp tip still gets a full rim.
    """
    count = len(points)

    if count < 3 or width <= 0:
        return [list(point) for point in points]

    center_x = sum(point[0] for point in points) / count
    center_y = sum(point[1] for point in points) / count

    def outward_normal(start, end):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)

        if length == 0.0:
            return None

        normal_x, normal_y = dy / length, -dx / length
        middle_x, middle_y = (start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0

        # Flip it if it points back toward the middle of the polygon.
        if (middle_x - center_x) * normal_x + (middle_y - center_y) * normal_y < 0.0:
            normal_x, normal_y = -normal_x, -normal_y

        return normal_x, normal_y

    outline = []

    for index, corner in enumerate(points):
        before = outward_normal(points[index - 1], corner)
        after = outward_normal(corner, points[(index + 1) % count])

        if before is None or after is None:
            outline.append(list(corner))
            continue

        miter_x, miter_y = before[0] + after[0], before[1] + after[1]
        miter_length = math.hypot(miter_x, miter_y)
        # How much further the corner reaches than the edges do.
        cosine = 0.0 if miter_length == 0.0 else (
            (miter_x * before[0] + miter_y * before[1]) / miter_length
        )

        if cosine <= 0.0 or 1.0 / cosine > miter_limit:
            outline.extend(__clip_miter__(
                corner, points[index - 1], points[(index + 1) % count],
                before, after, width, miter_limit,
            ))
        else:
            reach = width / cosine
            outline.append([
                corner[0] + miter_x / miter_length * reach,
                corner[1] + miter_y / miter_length * reach,
            ])

    return outline


def __clip_miter__(corner, previous, following, before, after, width, miter_limit):
    """
    The two points where the pushed-out edges either side of a sharp
    corner cross a line square to the corner's bisector, miter_limit
    * width out from the corner.
    """
    bisector_x, bisector_y = before[0] + after[0], before[1] + after[1]
    bisector_length = math.hypot(bisector_x, bisector_y)

    if bisector_length == 0.0:
        return [
            [corner[0] + before[0] * width, corner[1] + before[1] * width],
            [corner[0] + after[0] * width, corner[1] + after[1] * width],
        ]

    bisector_x, bisector_y = bisector_x / bisector_length, bisector_y / bisector_length
    clip_distance = miter_limit * width
    clipped = []

    for normal, toward in ((before, previous), (after, following)):
        # Along this pushed-out edge, heading away from the corner...
        edge_x, edge_y = corner[0] - toward[0], corner[1] - toward[1]
        edge_length = math.hypot(edge_x, edge_y) or 1.0
        edge_x, edge_y = edge_x / edge_length, edge_y / edge_length
        start_x, start_y = corner[0] + normal[0] * width, corner[1] + normal[1] * width
        # ...to where it reaches the clip line.
        start_reach = (start_x - corner[0]) * bisector_x + (start_y - corner[1]) * bisector_y
        step_reach = edge_x * bisector_x + edge_y * bisector_y
        travel = 0.0 if step_reach == 0.0 else (clip_distance - start_reach) / step_reach
        clipped.append([start_x + edge_x * travel, start_y + edge_y * travel])

    return clipped


def get_threat_style(threat_level: int) -> ThreatStyle:
    style = THREAT_STYLES.get(threat_level)

    return style if style is not None else ThreatStyle(MARKER_OUTLINE_COLOR)


def get_symbol_scale(style: ThreatStyle, seconds: float) -> float:
    """
    The style's size at this moment, pulse included.
    """
    if style.pulse_hz <= 0.0 or style.pulse_scale == 0.0:
        return style.scale

    # 0 -> 1 -> 0 once per pulse, starting at normal size.
    pulse = 0.5 - 0.5 * math.cos(2.0 * math.pi * style.pulse_hz * seconds)

    return style.scale + style.pulse_scale * pulse


def get_ring_progress(style: ThreatStyle, seconds: float) -> Optional[float]:
    """
    How far the pulse ring has travelled, 0.0 (just leaving the
    symbol, at the peak of a pulse) to 1.0 (fully out and faded), or
    None when the style has no ring.
    """
    if style.pulse_hz <= 0.0 or style.ring_scale <= 0.0:
        return None

    # The pulse peaks half way through each cycle.
    return (seconds * style.pulse_hz - 0.5) % 1.0


def is_blink_on(style: ThreatStyle, seconds: float) -> bool:
    """
    Blinking symbols are drawn in full for the first half of each
    blink, and as just a hairline outline for the second.
    """
    if style.flash_hz <= 0.0:
        return True

    return (seconds * style.flash_hz) % 1.0 < 0.5


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
        style = get_threat_style(marker.threat_level)
        seconds = get_system_time().timestamp()
        scale = get_symbol_scale(style, seconds)
        outline_color = style.outline_color
        # The rim stays the same width as the symbol grows, so a large
        # symbol still reads as an arrow, not a blob.
        outline_width = max(
            1, int(canvas.thin_line_width * MARKER_OUTLINE_WIDTH * style.outline_width)
        )

        if marker.track is not None:
            points = canvas.get_traffic_indicator(
                list(position), frame.heading, marker.track
            )

            if scale != 1.0:
                points = [
                    [
                        position[0] + (point[0] - position[0]) * scale,
                        position[1] + (point[1] - position[1]) * scale,
                    ]
                    for point in points
                ]
        else:
            points = None
            radius = max(1, int(canvas.no_direction_target_size * scale))

        self.__draw_pulse_ring__(frame, style, position, seconds)

        if not is_blink_on(style, seconds):
            self.__draw_blink_off__(frame, marker, style, position, points,
                                    radius if points is None else 0)

            return

        # The outline goes down first and the symbol is filled over
        # it, so only the rim outside the symbol shows.
        if points is not None:
            if outline_color is not None:
                drawing.renderer.polygon(
                    frame.framebuffer,
                    list(outline_color),
                    get_outline_polygon(
                        points,
                        outline_width * ARROW_OUTLINE_FRACTION + OUTLINE_PIXEL_ALLOWANCE,
                    ),
                    False,
                )

            drawing.renderer.polygon(
                frame.framebuffer,
                marker.color,
                points,
                not canvas.reduced_visuals,
            )
        else:
            if outline_color is not None:
                drawing.renderer.filled_circle(
                    frame.framebuffer,
                    list(outline_color),
                    list(position),
                    radius + outline_width,
                    False,
                )

            drawing.renderer.filled_circle(
                frame.framebuffer,
                marker.color,
                list(position),
                radius,
                not canvas.reduced_visuals,
            )

    def __draw_pulse_ring__(self, frame, style, position, seconds):
        """
        A ring that leaves the symbol at the peak of each pulse,
        expanding and fading to black as it goes.
        """
        progress = get_ring_progress(style, seconds)

        if progress is None or style.outline_color is None:
            return

        # The arrow's half length; the dot is half that.
        symbol_size = self.canvas.no_direction_target_size * 2
        peak_size = symbol_size * (style.scale + style.pulse_scale)
        radius = int(peak_size + (symbol_size * style.ring_scale - peak_size) * progress)
        fade = 1.0 - progress
        color = [int(channel * fade) for channel in style.outline_color[:3]]
        width = max(1, int(self.canvas.thin_line_width * style.ring_width))

        if radius > width:
            drawing.renderer.circle(frame.framebuffer, color, list(position), radius, width, False)

    def __draw_blink_off__(self, frame, marker, style, position, points, radius):
        """
        The "off" half of a blink: just a hairline outline of the
        symbol, or nothing at all.
        """
        if style.blink_outline_width <= 0.0:
            return

        color = list(style.outline_color or marker.color)
        width = max(1, int(self.canvas.thin_line_width * style.blink_outline_width))

        if points is not None:
            drawing.renderer.segments(frame.framebuffer, color, True, points, width, False)
        else:
            drawing.renderer.circle(frame.framebuffer, color, list(position), radius, width, False)

    def __draw_labels__(self, frame: ScopeFrame, marker: ScopeMarker, position):
        canvas = self.canvas
        label_color = list(marker.label_color or marker.color)
        # Below the symbol at its largest, so a pulsing symbol doesn't
        # run into its own labels.
        style = get_threat_style(marker.threat_level)
        largest = style.scale + max(0.0, style.pulse_scale)
        label_y = position[1] + int((canvas.no_direction_target_size << 2) * largest)

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
