"""
Rendering routines for OpenGl
"""

import math

import pygame
from common_utils import fast_math, generic_data_cache
from OpenGL import GL

RENDERER_NAME = "OpenGl"

__CONVERTED_TEXTURE_CACHE__ = generic_data_cache.GenericDataCache()


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


def __convert_texture__(
    texture: pygame.Surface
) -> list:
    converted = pygame.image.tostring(texture, "RGBA", True)
    size = texture.get_size()

    return converted, size


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
    key = "{}".format(hash(texture))

    rgba_data, size = __CONVERTED_TEXTURE_CACHE__.get_or_create_data(
        key,
        lambda: __convert_texture__(texture))

    # For some reason, OpenGl appears to "draw up"
    # starting at the Y position. So be need to adjust downwards
    # to make sure the sprite is using (X,Y) to be the
    # upper left cooridinate
    GL.glRasterPos2d(position[0], position[1] + size[1])
    GL.glDrawPixels(
        size[0],
        size[1],
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


def strip(
    framebuffer,
    color: list,
    top_points: list,
    bottom_points: list
):
    """
    Draws a filled strip between two parallel lines of points.
    Unlike polygon(), the strip may be curved (non-convex).

    Args:
        framebuffer (pygame.Surface): The surface to render to.
        color (list): The color to draw the strip.
        top_points (list): The points along one edge of the strip.
        bottom_points (list): The matching points along the other edge, in the same order.
    """

    __set_color__(color)

    GL.glBegin(GL.GL_TRIANGLE_STRIP)
    for top, bottom in zip(top_points, bottom_points):
        GL.glVertex2f(top[0], top[1])
        GL.glVertex2f(bottom[0], bottom[1])
    GL.glEnd()


# Holds (source surface, texture id, size) for the texture
# drawn by textured_disc so it is only uploaded when it changes.
__DISC_TEXTURE__ = None

__DISC_SEGMENTS__ = 72


def __get_disc_texture__(
    texture: pygame.Surface
):
    global __DISC_TEXTURE__

    if __DISC_TEXTURE__ is not None and __DISC_TEXTURE__[0] is texture:
        return __DISC_TEXTURE__[1], __DISC_TEXTURE__[2]

    if __DISC_TEXTURE__ is not None:
        GL.glDeleteTextures([__DISC_TEXTURE__[1]])

    # Turn the black (colorkey) pixels into transparent ones.
    size = texture.get_size()
    with_alpha = pygame.Surface(size, pygame.SRCALPHA, 32)
    with_alpha.fill((0, 0, 0, 0))
    keyed = texture.copy()
    keyed.set_colorkey((0, 0, 0))
    with_alpha.blit(keyed, (0, 0))
    rgba_data = pygame.image.tostring(with_alpha, "RGBA", False)

    texture_id = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
    GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    GL.glTexImage2D(
        GL.GL_TEXTURE_2D,
        0,
        GL.GL_RGBA,
        size[0],
        size[1],
        0,
        GL.GL_RGBA,
        GL.GL_UNSIGNED_BYTE,
        rgba_data)

    __DISC_TEXTURE__ = (texture, texture_id, size)

    return texture_id, size


def textured_disc(
    framebuffer,
    texture: pygame.Surface,
    texture_center: list,
    scale: list,
    rotation_degrees: float,
    screen_center: list,
    radius: int
):
    """
    Draws a circular section of a texture, scaled and rotated, onto the framebuffer.
    Black pixels in the texture are treated as transparent.

    Args:
        framebuffer: Ignored
        texture (pygame.Surface): The texture to draw from. Must not be modified after it is first drawn.
        texture_center (list): The (x, y) position in the texture, in fractional pixels, to place at the screen center.
        scale (list): The (x, y) number of screen pixels for each texture pixel.
        rotation_degrees (float): How far to rotate the texture counter-clockwise.
        screen_center (list): The center of the disc on screen.
        radius (int): The radius of the disc on screen.
    """
    if radius <= 0 or scale[0] <= 0.0 or scale[1] <= 0.0:
        return

    texture_id, size = __get_disc_texture__(texture)

    radians = math.radians(rotation_degrees)
    rotation_sin = math.sin(radians)
    rotation_cos = math.cos(radians)

    def get_texture_coordinate(screen_x: float, screen_y: float):
        # Undo the rotation, then the scale, to find the texture pixel.
        delta_x = screen_x - screen_center[0]
        delta_y = screen_y - screen_center[1]
        unrotated_x = (delta_x * rotation_cos) - (delta_y * rotation_sin)
        unrotated_y = (delta_x * rotation_sin) + (delta_y * rotation_cos)

        return (
            (texture_center[0] + (unrotated_x / scale[0])) / size[0],
            (texture_center[1] + (unrotated_y / scale[1])) / size[1])

    was_polygon_smooth = GL.glIsEnabled(GL.GL_POLYGON_SMOOTH)

    # Smoothing would leave seams between the triangles of the fan.
    GL.glDisable(GL.GL_POLYGON_SMOOTH)
    GL.glEnable(GL.GL_TEXTURE_2D)
    GL.glEnable(GL.GL_ALPHA_TEST)
    GL.glAlphaFunc(GL.GL_GREATER, 0.5)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
    GL.glColor3f(1.0, 1.0, 1.0)

    GL.glBegin(GL.GL_TRIANGLE_FAN)
    GL.glTexCoord2f(*get_texture_coordinate(screen_center[0], screen_center[1]))
    GL.glVertex2f(screen_center[0], screen_center[1])

    for segment_index in range(__DISC_SEGMENTS__ + 1):
        angle = (2.0 * math.pi * segment_index) / __DISC_SEGMENTS__
        edge_x = screen_center[0] + (math.cos(angle) * radius)
        edge_y = screen_center[1] + (math.sin(angle) * radius)
        GL.glTexCoord2f(*get_texture_coordinate(edge_x, edge_y))
        GL.glVertex2f(edge_x, edge_y)

    GL.glEnd()

    GL.glDisable(GL.GL_ALPHA_TEST)
    GL.glDisable(GL.GL_TEXTURE_2D)

    if was_polygon_smooth:
        GL.glEnable(GL.GL_POLYGON_SMOOTH)


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
        fast_math.get_circle_points(position[0], position[1], radius),
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
        fast_math.get_circle_points(position[0], position[1], radius),
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


# def __get_text_texture__(
#     font: pygame.font,
#     text: str,
#     color: list,
#     bg_color: list
# ):
#     textSurface = font.render(
#         text,
#         True,
#         color,
#         bg_color)
#     size_x, size_y = textSurface.get_width(), textSurface.get_height()
#     image = pygame.image.tostring(textSurface, "RGBX", True)
#     GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
#     texture_id = GL.glGenTextures(1)
#     GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
#     GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, 3, size_x, size_y, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, image)
#     GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
#     GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
#     GL.glTexEnvf(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_DECAL)

#     return texture_id, size_x, size_y


# texture_id, size_x, size_y = __get_text_texture__(
#     font,
#     text,
#     color,
#     bg_color)

# GL.glTranslated(position[0], position[1], 1)
# GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
# GL.glBegin(GL.GL_QUADS)
# GL.glTexCoord2f(0.0, 0.0)
# GL.glVertex2d(-1.0, -1.0)
# GL.glTexCoord2f(1.0, 0.0)
# GL.glVertex2d(1.0, -1.0)
# GL.glTexCoord2f(1.0, 1.0)
# GL.glVertex2d(1.0,  1.0)
# GL.glTexCoord2f(0.0, 1.0)
# GL.GL.glVertex2d(-1.0,  1.0)
# GL.glEnd()

# return size_x, size_y
