"""
Rendering routines for OpenGl
"""

import math

import pygame
from common_utils import fast_math
from OpenGL import GL

RENDERER_NAME = "OpenGl"


def __set_color__(
    color: list
) -> None:
    """
    Sets the color for OpenGL.
    Converts byte color (0 - 255) to 0.0 - 1.0 floating point.

    Args:
        color (list): List of colors (RGB) as bytes.
    """
    GL.glColor3f(
        color[0] / 255,
        color[1] / 255,
        color[2] / 255)


def draw_sprite(
    framebuffer,
    position: list,
    texture: pygame.Surface
):
    """
    Renders the sprite to the given positions

    Args:
        framebuffer: Ignored
        position (list): The position to draw the sprite
        texture (pygame.Surface): The sprite to draw.
    """
    size_x = texture.get_width()
    size_y = texture.get_height()
    rgba_data = pygame.image.tostring(texture, "RGBA", True)

    # For some reason, OpenGl appears to "draw up"
    # starting at the Y position. So be need to adjust downwards
    # to make sure the sprite is using (X,Y) to be the
    # upper left cooridinate
    GL.glRasterPos2d(position[0], position[1] + size_y)
    GL.glDrawPixels(
        size_x,
        size_y,
        GL.GL_RGBA,
        GL.GL_UNSIGNED_BYTE,
        rgba_data)


def polygon(
    framebuffer,
    color: list,
    points: list,
    is_antialiased: bool = True
):
    """
    Draws a filled polygon from the given points with the given color to the given surface.

    Args:
        framebuffer (pygame.Surface): The surface to render to.
        color (list): The color to draw the polygon.
        points (list): The points that make up the polygon.
        is_antialiased (bool, optional): Should an anti-aliased outline but drawn?. Defaults to True.
    """

    __set_color__(color)

    GL.glBegin(GL.GL_POLYGON)
    [GL.glVertex2f(point[0], point[1]) for point in points]
    GL.glEnd()


def circle(
    framebuffer,
    color: list,
    position: list,
    radius: int,
    width: int = 1,
    is_antialiased: bool = True
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

    segments(
        None,
        color,
        True,
        fast_math.get_circle_points(position, radius),
        width,
        is_antialiased)


def filled_circle(
    framebuffer,
    color: list,
    position: list,
    radius: int,
    is_antialiased: bool = True
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

    polygon(
        None,
        color,
        fast_math.get_circle_points(position, radius),
        is_antialiased)


def segments(
    framebuffer,
    color: list,
    is_closed: bool,
    points: list,
    width: int = 1,
    is_antialiased: bool = True
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
            None,
            color,
            points[point_index - 1],
            points[point_index],
            width,
            is_antialiased)

    if is_closed:
        segment(
            None,
            color,
            points[points_count - 1],
            points[0],
            width,
            is_antialiased)


def segment(
    framebuffer,
    color: list,
    start: list,
    end: list,
    width: int = 1,
    is_antialiased: bool = True
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
    slope = 100.0
    if run != 0:
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

    # segments_to_draw = [starting_points[0], ending_points[0],
    #                     ending_points[1], starting_points[1]]

    # We need to draw the filled polygon
    # THEN draw an anti-aliased outline around it
    # due to the lack of a "aa_filled_polygon"

    __set_color__(color)

    GL.glBegin(GL.GL_QUADS)
    GL.glVertex2f(starting_points[0][0], starting_points[0][1])
    GL.glVertex2f(ending_points[0][0], ending_points[0][1])
    GL.glVertex2f(ending_points[1][0], ending_points[1][1])
    GL.glVertex2f(starting_points[1][0], starting_points[1][1])
    GL.glEnd()
