import testing

testing.load_imports()

import configuration

def apply_declination(heading):
    """
    Returns a heading to display with the declination adjust to convert from true to magnetic.

    Arguments:
        heading {float} -- The TRUE heading.

    Returns:
        float -- The MAGNETIC heading.
    """

    try:
        new_heading = int(heading - configuration.CONFIGURATION.get_declination())
    except:
        # If the heading is the unknown '---' then the math wil fail.
        return heading

    if new_heading < 0.0:
        new_heading = new_heading + 360

    if new_heading > 360.0:
        new_heading = new_heading - 360

    return new_heading
