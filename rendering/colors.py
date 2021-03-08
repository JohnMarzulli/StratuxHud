"""
Module to define common colors, and the math to work with them.
"""

from common_utils.fast_math import interpolate

BLACK = (0,   0,   0)
DARK_GRAY = (64, 64, 64)
GRAY = (128, 128, 128)
WHITE = (255, 255, 255)
BLUE = (0,   0, 255)
GREEN = (0, 255,   0)
RED = (255,   0,   0)
YELLOW = (255, 255, 0)


def get_color_mix(
    left_color,
    right_color,
    proportion: float
):
    """
    Returns a color that is a mix between the two given colors.
    A given proportion of 0 would return the left color.
    A given proportion of 1 would return the right_color.
    A given proportion of 0.5 would return a 50/50 mix.

    Works for RGB or ARGB, but both sides MUST have matching number of components.

    >>> get_color_mix([0,0,0], [255, 255, 255], 0.0)
    [0, 0, 0]

    >>> get_color_mix([0,0,0], [255, 255, 255], 1.0)
    [255, 255, 255]

    >>> get_color_mix([0,0,0], [255, 255, 255], 0.5)
    [127, 127, 127]

    >>> get_color_mix([125,255,0], [125, 0, 255], 0.5)
    [125, 127, 127]

    Arguments:
        left_color {float[]} -- The starting color.
        right_color {float[]} -- The ending color.
        proportion {float} -- The mix between the two colors.

    Returns:
        float[] -- The new color.
    """

    array_length = len(left_color)
    if array_length != len(right_color):
        return left_color

    indices = range(0, array_length)
    new_color = [int(interpolate(left_color[index], right_color[index], proportion)) for index in indices]

    return new_color


if __name__ == '__main__':
    import doctest

    print("Starting tests.")

    doctest.testmod()

    print("Tests finished")
