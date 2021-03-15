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


def clamp(
    minimum,
    value,
    maximum
):
    """
    Makes sure the given value (middle param) is always between the maximum and minimum.

    Arguments:
        minimum {number} -- The smallest the value can be (inclusive).
        value {number} -- The value to clamp.
        maximum {number} -- The largest the value can be (inclusive).

    Returns:
        number -- The value within the allowable range.

    >>> clamp(0, 15, 30)
    15
    >>> clamp(0, 0, 30)
    0
    >>> clamp(0, 30, 30)
    30
    >>> clamp(0, -1, 30)
    0
    >>> clamp(0, 31, 30)
    30
    """

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def interpolatef(
    left_value,
    right_value,
    proportion: float
) -> float:
    """
    Finds the spot between the two values.

    Arguments:
        left_value {number} -- The value on the "left" that 0.0 would return.
        right_value {number} -- The value on the "right" that 1.0 would return.
        proportion {float} -- The proportion from the left to the right hand side.

    >>> interpolatef(0, 255, 0.5)
    127.5
    >>> interpolatef(10, 20, 0.5)
    15.0
    >>> interpolatef(0, 255, 0.0)
    0.0
    >>> interpolatef(0, 255, 0)
    0.0
    >>> interpolatef(0, 255, 1)
    255.0
    >>> interpolatef(0, 255, 1.5)
    255.0
    >>> interpolatef(0, 255, -0.5)
    0.0
    >>> interpolatef(0, 255, 0.1)
    25.5
    >>> interpolatef(0, 255, 0.9)
    229.5
    >>> interpolatef(255, 0, 0.5)
    127.5
    >>> interpolatef(20, 10, 0.5)
    15.0
    >>> interpolatef(255, 0, 0.0)
    255.0
    >>> interpolatef(255, 0, 0)
    255.0
    >>> interpolatef(255, 0, 1)
    0.0
    >>> interpolatef(255, 0, 1.5)
    0.0
    >>> interpolatef(255, 0, -0.5)
    255.0
    >>> interpolatef(255, 0, 0.1)
    229.5
    >>> interpolatef(255, 0, 0.9)
    25.5
    >>> interpolatef(0, 255, 0.9)
    229.5
    >>> interpolatef(0, 510, 0.9)
    459.0
    >>> interpolatef(510, 0, 0.9)
    51.0
    >>> interpolatef(510, 0, 0.95)
    25.5

    Returns:
        float -- The number that is the given amount between the left and right.
    """

    true_left_value = left_value if left_value < right_value else right_value
    true_right_value = right_value if left_value < right_value else left_value

    proportion = clamp(0.0, proportion, 1.0)

    calculated_target = float(float(left_value) + (float(right_value - float(left_value)) * float(proportion)))

    return clamp(
        true_left_value,
        calculated_target,
        true_right_value)


def interpolate(
    left_value,
    right_value,
    proportion: float
) -> int:
    """
    Finds the spot between the two values.

    Arguments:
        left_value {number} -- The value on the "left" that 0.0 would return.
        right_value {number} -- The value on the "right" that 1.0 would return.
        proportion {float} -- The proportion from the left to the right hand side.

    >>> interpolate(0, 255, 0.5)
    127
    >>> interpolate(10, 20, 0.5)
    15
    >>> interpolate(0, 255, 0.0)
    0
    >>> interpolate(0, 255, 0)
    0
    >>> interpolate(0, 255, 1)
    255
    >>> interpolate(0, 255, 1.5)
    255
    >>> interpolate(0, 255, -0.5)
    0
    >>> interpolate(0, 255, 0.1)
    25
    >>> interpolate(0, 255, 0.9)
    229
    >>> interpolate(255, 0, 0.5)
    127
    >>> interpolate(20, 10, 0.5)
    15
    >>> interpolate(255, 0, 0.0)
    255
    >>> interpolate(255, 0, 0)
    255
    >>> interpolate(255, 0, 1)
    0
    >>> interpolate(255, 0, 1.5)
    0
    >>> interpolate(255, 0, -0.5)
    255
    >>> interpolate(255, 0, 0.1)
    229
    >>> interpolate(255, 0, 0.9)
    25
    >>> interpolate(0, 255, 0.9)
    229
    >>> interpolate(0, 510, 0.9)
    459
    >>> interpolate(510, 0, 0.9)
    51

    Returns:
        int -- The number that is the given amount between the left and right.
    """
    return int(interpolatef(left_value, right_value, proportion))


def rangef(
    start: float,
    stop: float,
    step: float
) -> list:
    while start < stop:
        yield float(start)
        start += step


def get_circle_points(
    center: list,
    radius: float,
) -> list:
    """
    Given a center and a radius, find the points to make a
    smooth circle. The number of srgments is automatically
    determined by the radius.

    Args:
        center (list): The center of the circle.
        radius (float): The radius of the circle.

    Returns:
        list: The points that make the circle.
    """
    angle_chunks = math.sqrt(radius / 2.0)
    arc_radians = (angle_chunks / radius)
    arc_radians = max(0.1, arc_radians)

    points = [[int(center[0] + (radius * math.sin(radian))), int(center[1] + (radius * math.cos(radian)))] for radian in rangef(0, TWO_PI, arc_radians)]

    return points


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

    if angle >= 360.0:
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
    """
    Given an angle in degrees, returns the angle in radians.

    Args:
        degrees (float): The angle in degrees.

    Returns:
        float: The angle in radians.
    """
    clamped_degrees = int(wrap_degrees(degrees))
    return __RADIANS_BY_DEGREES__[clamped_degrees]


def get_degrees(
    radians: float
) -> float:
    """
    Given an angle in radians, returns the angle in degrees.

    Args:
        radians (float): The angle to convert, in radians.

    Returns:
        float: The angle converted to degrees.
    """
    clamped_radians = wrap_radians(radians)
    indexed_radians = int(clamped_radians * 100)

    return __DEGREES_BY_RADIANS___[indexed_radians]


def sin(
    degrees: float
) -> float:
    """
    Get the sin of an angle in degrees.

    Args:
        degrees (float): The angle in degrees.

    Returns:
        float: The sin of the angle.
    """
    clamped_degs = int(wrap_degrees(degrees))
    return SIN_BY_DEGREES[clamped_degs]


def cos(
    degrees: float
) -> float:
    """
    Get the cos of an angle in degrees.

    Args:
        degrees (float): The angle in degrees.

    Returns:
        float: The cos of the angle.
    """
    clamped_degs = int(wrap_degrees(degrees))
    return COS_BY_DEGREES[clamped_degs]


def tan(
    degrees: float
) -> float:
    """
    Get the tan of an angle in degrees.

    Args:
        degrees (float): The angle in degrees.

    Returns:
        float: The tan of the angle.
    """
    clamped_degs = int(wrap_degrees(degrees))
    return TAN_BY_DEGREES[clamped_degs]


def translate_points(
    list_of_points: list,
    translation: list
) -> list:
    """
    Moves a set of points by the given x/y component.

    Args:
        list_of_points (list): The points to translate.
        translation (list): How much to translate the points by.

    Returns:
        list: The original points that have been translated.
    """

    return [[point[0] + translation[0],
             point[1] + translation[1]] for point in list_of_points]


def rotate_points(
    list_of_points: list,
    rotation_center: list,
    rotation_degrees: float
) -> list:
    """
    Rotates all of the given points around the given center.

    Args:
        list_of_points (list): The points to rotate.
        rotation_center (list): The point of rotation. This is so the point of rotation can be other than 0,0
        rotation_degrees (float): How much to rotate the points by.

    Returns:
        list: The collection of points that have been rotated.
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


if __name__ == '__main__':
    import doctest

    print("Starting tests.")

    doctest.testmod()

    print("Finished tests.")
