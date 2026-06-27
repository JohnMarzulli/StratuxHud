"""
Rendering routines for the default PyGame software renderer.
"""

import pygame
import pygame.gfxdraw
from common_utils import generic_data_cache
from common_utils.local_debug import IS_PI

RENDERER_NAME = "Rasterization"

__TEXT_CACHE__ = generic_data_cache.GenericDataCache()


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
    is_antialiased: bool = not IS_PI
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
        # A single native call to outline the polygon, instead of
        # re-walking every edge through segment()'s fill+AA pass.
        pygame.gfxdraw.aapolygon(
            framebuffer,
            points,
            color)


def circle(
    framebuffer: pygame.Surface,
    color: list,
    position: list,
    radius: int,
    width: int = 1,
    is_antialiased: bool = not IS_PI
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

    center_x = int(position[0])
    center_y = int(position[1])
    radius = int(radius)
    width = int(width)

    if not is_antialiased:
        pygame.draw.circle(
            framebuffer,
            color,
            (center_x, center_y),
            radius,
            width)
        return

    if width <= 1:
        pygame.gfxdraw.aacircle(
            framebuffer,
            center_x,
            center_y,
            radius,
            color)
        return

    # Fill the ring with the fast (non-AA) native circle, then smooth
    # only the inner and outer edges with two cheap AA outline calls.
    # This replaces what used to be an O(sqrt(radius)) chain of
    # rotated, filled-then-outlined quads.
    pygame.draw.circle(
        framebuffer,
        color,
        (center_x, center_y),
        radius,
        width)
    pygame.gfxdraw.aacircle(
        framebuffer,
        center_x,
        center_y,
        radius,
        color)
    pygame.gfxdraw.aacircle(
        framebuffer,
        center_x,
        center_y,
        max(0, radius - width),
        color)


def filled_circle(
    framebuffer: pygame.Surface,
    color: list,
    position: list,
    radius: int,
    is_antialiased: bool = not IS_PI
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

    center_x = int(position[0])
    center_y = int(position[1])
    radius = int(radius)

    pygame.gfxdraw.filled_circle(
        framebuffer,
        center_x,
        center_y,
        radius,
        color)

    if is_antialiased:
        pygame.gfxdraw.aacircle(
            framebuffer,
            center_x,
            center_y,
            radius,
            color)


def segments(
    framebuffer: pygame.Surface,
    color: list,
    is_closed: bool,
    points: list,
    width: int = 1,
    is_antialiased: bool = not IS_PI
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

    if len(points) < 2:
        return

    # A single native multi-segment draw instead of one segment() call
    # (each of which used to do a fill + AA outline pass) per edge.
    if is_antialiased and width <= 1:
        pygame.draw.aalines(
            framebuffer,
            color,
            is_closed,
            points)
    else:
        pygame.draw.lines(
            framebuffer,
            color,
            is_closed,
            points,
            max(1, int(width)))


def segment(
    framebuffer: pygame.Surface,
    color: list,
    start: list,
    end: list,
    width: int = 1,
    is_antialiased: bool = not IS_PI
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

    if is_antialiased and width <= 1:
        pygame.draw.aaline(
            framebuffer,
            color,
            start,
            end)
    else:
        pygame.draw.line(
            framebuffer,
            color,
            start,
            end,
            max(1, int(width)))
