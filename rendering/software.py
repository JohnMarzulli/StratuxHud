"""
Rendering routines for the default PyGame software renderer.
"""

import math

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


def strip(
    framebuffer: pygame.Surface,
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

    pygame.draw.polygon(
        framebuffer,
        color,
        top_points + bottom_points[::-1],
        0)  # Make filled


# Only one map is drawn at a time, so a single entry is enough.
# Holding a reference to the texture keeps its id from being reused.
__TEXTURED_DISC_CACHE__ = {}

# Used as the "see through" color of the disc mask.
# Must not be a color that the textures use.
__MASK_KEY_COLOR__ = (255, 0, 255)


def __get_disc_mask__(
    framebuffer: pygame.Surface,
    radius: int
):
    """
    Returns a working surface the size of the disc, and a mask
    that is black outside of the disc and transparent inside.
    """
    cached = __TEXTURED_DISC_CACHE__.get("mask")

    if cached is not None and cached[0] == radius:
        return cached[1], cached[2]

    size = (radius << 1, radius << 1)
    working = pygame.Surface(size, 0, framebuffer)
    working.set_colorkey((0, 0, 0))

    mask = pygame.Surface(size, 0, framebuffer)
    mask.fill((0, 0, 0))
    pygame.draw.circle(mask, __MASK_KEY_COLOR__, (radius, radius), radius)
    mask.set_colorkey(__MASK_KEY_COLOR__)

    __TEXTURED_DISC_CACHE__["mask"] = (radius, working, mask)

    return working, mask


def textured_disc(
    framebuffer: pygame.Surface,
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

    The expensive scale and rotate are cached, and only performed again
    when the rotation (to the nearest degree), scale, or the texture pixel
    under the center changes.

    Args:
        framebuffer (pygame.Surface): The surface to render to.
        texture (pygame.Surface): The texture to draw from. Must not be modified after it is first drawn.
        texture_center (list): The (x, y) position in the texture, in fractional pixels, to place at the screen center.
        scale (list): The (x, y) number of screen pixels for each texture pixel.
        rotation_degrees (float): How far to rotate the texture counter-clockwise.
        screen_center (list): The center of the disc on screen.
        radius (int): The radius of the disc on screen.
    """
    radius = int(radius)

    if radius <= 0 or scale[0] <= 0.0 or scale[1] <= 0.0:
        return

    # The part of the texture that covers the disc, no matter the rotation.
    crop_left = math.floor(texture_center[0] - (radius / scale[0]))
    crop_top = math.floor(texture_center[1] - (radius / scale[1]))
    crop_size = (
        math.ceil(texture_center[0] + (radius / scale[0])) - crop_left + 1,
        math.ceil(texture_center[1] + (radius / scale[1])) - crop_top + 1)
    scaled_size = (
        max(1, int(crop_size[0] * scale[0] + 0.5)),
        max(1, int(crop_size[1] * scale[1] + 0.5)))
    rotation_degrees = int(round(rotation_degrees)) % 360

    key = (crop_left, crop_top, crop_size, scaled_size, rotation_degrees)
    cached = __TEXTURED_DISC_CACHE__.get("map")

    if cached is not None and cached[0] is texture and cached[1] == key:
        rotated = cached[2]
    else:
        cropped = pygame.Surface(crop_size, 0, framebuffer)
        cropped.fill((0, 0, 0))
        cropped.blit(texture, (-crop_left, -crop_top))

        # Nearest neighbor scaling keeps every texture pixel a crisp block.
        scaled = pygame.transform.scale(cropped, scaled_size)
        scaled.set_colorkey((0, 0, 0))
        rotated = pygame.transform.rotate(scaled, rotation_degrees)

        __TEXTURED_DISC_CACHE__["map"] = (texture, key, rotated)

    # Find where the texture center ended up after scaling and rotating.
    offset_x = (texture_center[0] - crop_left) * \
        (scaled_size[0] / crop_size[0]) - (scaled_size[0] / 2.0)
    offset_y = (texture_center[1] - crop_top) * \
        (scaled_size[1] / crop_size[1]) - (scaled_size[1] / 2.0)
    radians = math.radians(rotation_degrees)
    rotation_sin = math.sin(radians)
    rotation_cos = math.cos(radians)
    rotated_center_x = (rotated.get_width() / 2.0) + \
        (offset_x * rotation_cos) + (offset_y * rotation_sin)
    rotated_center_y = (rotated.get_height() / 2.0) - \
        (offset_x * rotation_sin) + (offset_y * rotation_cos)

    working, mask = __get_disc_mask__(framebuffer, radius)
    working.fill((0, 0, 0))
    working.blit(
        rotated,
        (int(round(radius - rotated_center_x)), int(round(radius - rotated_center_y))))
    working.blit(mask, (0, 0))

    framebuffer.blit(
        working,
        (int(round(screen_center[0])) - radius, int(round(screen_center[1])) - radius))


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
