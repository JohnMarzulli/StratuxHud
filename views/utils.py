from configuration import configuration


def apply_declination(
    heading
) -> int:
    """
    Returns a heading to display with the declination adjust to convert from true to magnetic.

    Arguments:
        heading {float} -- The TRUE heading.

    Returns:
        float -- The MAGNETIC heading.
    """

    try:
        declination_applied = heading - configuration.CONFIGURATION.get_declination()
        new_heading = int(declination_applied)
    except:
        # If the heading is the unknown '---' then the math wil fail.
        return heading

    if new_heading < 0.0:
        new_heading = new_heading + 360

    if new_heading > 360.0:
        new_heading = new_heading - 360

    return new_heading
