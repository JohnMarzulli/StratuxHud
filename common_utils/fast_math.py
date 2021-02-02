"""
Shared code to help speed up various math functions.
"""

import math

SIN_BY_DEGREES = {}
COS_BY_DEGREES = {}
TAN_BY_DEGREES = {}

__RADIANS_BY_DEGREES__ = {}
__DEGREES_BY_RADIANS___ = {}

TWO_PI = 2.0 * math.pi

# Fill the quick trig look up tables.
for __degrees__ in range(0, 361):
    __radians__ = math.radians(__degrees__)

    __RADIANS_BY_DEGREES__[__degrees__] = __radians__

    SIN_BY_DEGREES[__degrees__] = math.sin(__radians__)
    COS_BY_DEGREES[__degrees__] = math.cos(__radians__)
    TAN_BY_DEGREES[__degrees__] = math.tan(__radians__)

for __indexed_radians__ in range(0, int(TWO_PI * 100)):
    __actual_radians__ = __indexed_radians__ / 100.0
    __DEGREES_BY_RADIANS___[
        __indexed_radians__] = math.degrees(__actual_radians__)


def wrap_degrees(
    angle: float
) -> float:
    """
    Wraps an angle (degrees) to be between 0.0 and 360
    Arguments:
        angle {float} -- The input angle
    Returns: and value that is between 0 and 360, inclusive.
    """

    if angle < 0.0:
        return wrap_degrees(angle + 360.0)

    if angle > 360.0:
        return wrap_degrees(angle - 360.0)

    return angle


def wrap_radians(
    radians: float
) -> float:
    """
    Wraps an angle that is in radians to be between 0.0 and 2Pi
    Arguments:
        angle {float} -- The input angle
    Returns: and value that is between 0 and 2Pi, inclusive.
    """
    if radians < 0.0:
        return wrap_radians(radians + TWO_PI)

    if radians > TWO_PI:
        return wrap_radians(radians - TWO_PI)

    return radians


def get_radians(
    degrees: float
) -> float:
    clamped_degrees = int(wrap_degrees(degrees))
    return __RADIANS_BY_DEGREES__[clamped_degrees]


def get_degrees(
    radians: float
) -> float:
    clamped_radians = wrap_radians(radians)
    indexed_radians = int(clamped_radians * 100)

    return __DEGREES_BY_RADIANS___[indexed_radians]


def sin(
    degrees: float
) -> float:
    clamped_degs = int(wrap_degrees(degrees))
    return SIN_BY_DEGREES[clamped_degs]


def cos(
    degrees: float
) -> float:
    clamped_degs = int(wrap_degrees(degrees))
    return COS_BY_DEGREES[clamped_degs]


def tan(
    degrees: float
) -> float:
    clamped_degs = int(wrap_degrees(degrees))
    return TAN_BY_DEGREES[clamped_degs]


def translate_points(
    list_of_points: list,
    translation: list
) -> list:
    return [[point[0] + translation[0],
            point[1] + translation[1]] for point in list_of_points]


def rotate_points(
    list_of_points: list,
    rotation_center: list,
    rotation_degrees: float
) -> list:
    """Generates the coordinates for a reticle indicating
    traffic is above use.

    Arguments:
        center_x {int} -- Center X screen position
        center_y {int} -- Center Y screen position
        scale {float} -- The scale of the reticle relative to the screen.
    """

    # 2 - determine the angle of rotation compared to our "up"
    rotation_degrees = int(wrap_degrees(rotation_degrees))

    detranslated_points = translate_points(
        list_of_points,
        [-rotation_center[0], -rotation_center[1]])

    # 3 - Rotate the zero-based points
    rotation_sin = SIN_BY_DEGREES[rotation_degrees]
    rotation_cos = COS_BY_DEGREES[rotation_degrees]
    rotated_points = [[point[0] * rotation_cos - point[1] * rotation_sin,
                       point[0] * rotation_sin + point[1] * rotation_cos] for point in detranslated_points]

    translated_points = translate_points(rotated_points, rotation_center)

    return translated_points
