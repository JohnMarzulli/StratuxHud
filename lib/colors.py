import copy


def clamp(minimum, value, maximum):
    """
    Makes sure the given value (middle param) is always between the maximum and minimum.

    Arguments:
        minimum {number} -- The smallest the value can be (inclusive).
        value {number} -- The value to clamp.
        maximum {number} -- The largest the value can be (inclusive).

    Returns:
        number -- The value within the allowable range.
    """

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def interpolate(left_value, right_value, proportion):
    """
    Finds the spot between the two values.

    Arguments:
        left_value {number} -- The value on the "left" that 0.0 would return.
        right_value {number} -- The value on the "right" that 1.0 would return.
        proportion {float} -- The proportion from the left to the right hand side.

    Returns:
        float -- The number that is the given amount between the left and right.
    """

    left_value = clamp(0, left_value, 255)
    right_value = clamp(0, right_value, 255)
    proportion = clamp(0.0, proportion, 1.0)

    return clamp(0,
                 int(float(left_value) +
                     (float(right_value - left_value) * proportion)),
                 255)


def get_color_mix(left_color, right_color, proportion):
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

    indices = list(range(0, array_length))
    new_color = [int(interpolate(left_color[index], right_color[index], proportion)) for index in indices]

    return new_color


if __name__ == '__main__':
    import doctest

    print("Starting tests.")

    doctest.testmod()

    print("Tests finished")
