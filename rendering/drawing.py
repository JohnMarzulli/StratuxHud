"""
Module to abstract and centralize rendering code.
"""

import math

import pygame
import pygame.gfxdraw
from common_utils import fast_math


def filled_circle(
    framebuffer: pygame.Surface,
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
        position[0],
        position[1],
        radius,
        color)

    if is_antialiased:
        pygame.gfxdraw.aacircle(
            framebuffer,
            position[0],
            position[1],
            radius,
            color)


def segment(
    framebuffer: pygame.Surface,
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
    if not is_antialiased or rise == 0 or run == 0:
        pygame.draw.line(
            framebuffer,
            color,
            start,
            end,
            width)
    else:
        slope = rise / float(run)
        degrees = math.atan(slope)
        half_thickness = width / 2.0

        # start with the assumption of a veritcal
        # line. Calculate the points to the left
        # and right
        end_points_to_rotate = [[-half_thickness, 0], [half_thickness, 0]]
        amount_to_rotate = degrees + 90
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

        segments = [starting_points[0], ending_points[0],
                    ending_points[1], starting_points[1]]

        # We need to draw the filled polygon
        # THEN draw an anti-aliased outline around it
        # due to the lack of a "aa_filled_polygon"
        pygame.draw.polygon(
            framebuffer,
            color,
            segments)
        pygame.gfxdraw.aapolygon(
            framebuffer,
            segments,
            color)
