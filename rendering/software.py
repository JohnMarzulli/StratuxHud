"""
Rendering routines for the default PyGame software renderer.
"""

import math

import pygame
import pygame.gfxdraw
from common_utils import fast_math
from common_utils.local_debug import IS_SLOW


RENDERER_NAME = "Rasterization"


def draw_sprite(
    framebuffer: pygame.Surface,
    position: list,
    texture: pygame.Surface
):
    """
    Renders the sprite to the given positions

    Args:
        framebuffer (pygame.Surface): [description]
        position (list): The position to draw the sprite
        texture (pygame.Surface): The sprite to draw.
    """
    if framebuffer is None:
        return

    framebuffer.blit(texture, position)


def polygon(
    framebuffer: pygame.Surface,
    color: list,
    points: list,
    is_antialiased: bool = not IS_SLOW
):
    """
    Draws a filled polygon from the given points with the given color to the given surface.

    Args:
        framebuffer (pygame.Surface): The surface to render to.
        color (list): The color to draw the polygon.
        points (list): The points that make up the polygon.
        is_antialiased (bool, optional): Should an anti-aliased outline but drawn?. Defaults to True.
    """

    pygame.draw.polygon(
        framebuffer,
        color,
        points,
        0)  # Make filled

    if is_antialiased:
        segments(
            framebuffer,
            color,
            True,
            points,
            1)


def circle(
    framebuffer: pygame.Surface,
    color: list,
    position: list,
    radius: int,
    width: int = 1,
    is_antialiased: bool = not IS_SLOW
):
    """
    Draws an outline of a cicle at the given position with the given radius and given width

    Args:
        framebuffer (pygame.Surface): The target surface to draw the line segment onto
        color (list): The color of the line segment
        position (list): The center of the circle
        radius (int): How many pixels wide the circle is
        width (int): How wide the line is. Defaults to 1
        is_antialiased (bool, optional): Should the circle be drawn anti aliased. Defaults to False.
    """

    pygame.draw.circle(
        framebuffer,
        color,
        position,
        radius,
        width)

    if is_antialiased:
        half_width = width / 2.0

        # for any thickness, we need to draw
        # around the outside and inside
        # of the outline to make sure it is smoothe

        pygame.gfxdraw.aacircle(
            framebuffer,
            position[0],
            position[1],
            int(radius + half_width - 0.5),
            color)

        pygame.gfxdraw.aacircle(
            framebuffer,
            position[0],
            position[1],
            int(radius - half_width - 0.5),
            color)


def filled_circle(
    framebuffer: pygame.Surface,
    color: list,
    position: list,
    radius: int,
    is_antialiased: bool = not IS_SLOW
):
    """
    Draws a filled cicle at the given position with the given radius.

    Args:
        framebuffer (pygame.Surface): The target surface to draw the line segment onto
        color (list): The color of the line segment
        position (list): The center of the circle
        radius (int): How many pixels wide the circle is
        is_antialiased (bool, optional): Should the circle be drawn anti aliased. Defaults to False.
    """

    # We need top draw the filled circle
    # THEN the AA circle due to the filled
    # circle being a traditional (thus aliased)
    # polygon.
    #
    # Doing the aacircle ONLY draws the outline.
    # Drawing both in this order allows for
    # the appearence of a filled, anti-aliased circle.
    pygame.gfxdraw.filled_circle(
        framebuffer,
        int(position[0]),
        int(position[1]),
        int(radius),
        color)

    if is_antialiased:
        pygame.gfxdraw.aacircle(
            framebuffer,
            int(position[0]),
            int(position[1]),
            int(radius),
            color)


def segments(
    framebuffer: pygame.Surface,
    color: list,
    is_closed: bool,
    points: list,
    width: int = 1,
    is_antialiased: bool = not IS_SLOW
):
    """
    Draws segements using the given points.
    The first point is the start, and each point is then
    connected together using the given colors and width.

    Can optionally draw the line anti-aliased

    Args:
        framebuffer (pygame.Surface): The target surface to draw the line segment onto
        color (list): The color of the line segment
        is_closed (bool): Should the first and last points be joined to close a polygon?
        points (list): A list of tuples (x,y) of each position to connect together with segments.
        width (int, optional): The width (in pixels) of the line segment. The theoretical single pixel line is defined by the points, with the additional pixels drawn above and below. Defaults to 1.
        is_antialiased (bool, optional): Should the line segment be drawn anti aliased. Defaults to False.
    """

    points_count = len(points)

    for point_index in range(1, points_count):
        segment(
            framebuffer,
            color,
            points[point_index - 1],
            points[point_index],
            width,
            is_antialiased)

    if is_closed:
        segment(
            framebuffer,
            color,
            points[points_count - 1],
            points[0],
            width,
            is_antialiased)


def segment(
    framebuffer: pygame.Surface,
    color: list,
    start: list,
    end: list,
    width: int = 1,
    is_antialiased: bool = not IS_SLOW
):
    """
    Draws a single line segment of the given color,
    from the given start point, to the given endpoint,
    of the given width.

    Can optionally draw the line anti-aliased

    Args:
        framebuffer (pygame.Surface): The target surface to draw the line segment onto
        color (list): The color of the line segment
        start (list): The starting (x,y) position of the line segment.
        end (list): The ending (x,y) position of the line segment.
        width (int, optional): The width (in pixels) of the line segment. The theoretical single pixel line is defined by the points, with the additional pixels drawn above and below. Defaults to 1.
        is_antialiased (bool, optional): Should the line segment be drawn anti aliased. Defaults to False.
    """
    rise = start[1] - end[1]
    run = start[0] - end[0]

    # Never divide by zero. Also veritical and
    # horizontal lines can not gain anything
    # from anti-aliasing
    if not is_antialiased or rise == 0 or run == 0:
        pygame.draw.line(
            framebuffer,
            color,
            start,
            end,
            width)
    else:
        slope = rise / float(run)
        degrees = math.degrees(math.atan(slope))
        half_thickness = width / 2.0

        # start with the assumption of a veritcal
        # line. Calculate the points to the left
        # and right
        end_points_to_rotate = [[-half_thickness, 0], [half_thickness, 0]]
        amount_to_rotate = degrees + 90.0
        rotated_endpoints = fast_math.rotate_points(
            end_points_to_rotate,
            [0, 0],
            amount_to_rotate)
        starting_points = [
            [start[0] + rotated_endpoints[0][0],
                start[1] + rotated_endpoints[0][1]],
            [start[0] + rotated_endpoints[1][0], start[1] + rotated_endpoints[1][1]]]
        ending_points = [
            [end[0] + rotated_endpoints[0][0], end[1] + rotated_endpoints[0][1]],
            [end[0] + rotated_endpoints[1][0], end[1] + rotated_endpoints[1][1]]]

        segments_to_draw = [starting_points[0], ending_points[0],
                            ending_points[1], starting_points[1]]

        # We need to draw the filled polygon
        # THEN draw an anti-aliased outline around it
        # due to the lack of a "aa_filled_polygon"
        pygame.draw.polygon(
            framebuffer,
            color,
            segments_to_draw)

        pygame.gfxdraw.aapolygon(
            framebuffer,
            segments_to_draw,
            color)
