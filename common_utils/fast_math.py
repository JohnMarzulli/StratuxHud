"""
Shared code to help speed up various math functions.
"""

import math
from views.hud_elements import COS_RADIANS_BY_DEGREES

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
