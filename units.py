"""
For converting units.
"""

STATUTE = "statute"
NAUTICAL = "knots"
METRIC = "metric"

SPEED = "SPEED"
DISTANCE = "DISTANCE"

UNIT_LABELS = {
    STATUTE: {SPEED: "MPH", DISTANCE: "SM"},
    NAUTICAL: {SPEED: "KTS", DISTANCE: "NM"},
    METRIC: {SPEED: "KPH", DISTANCE: "KM"}
}


feet_to_nm = 6076.12
feet_to_sm = 5280.0
feet_to_km = 3280.84
feet_to_m = 3.28084
mph_to_ms = 0.44704

IMPERIAL_NEARBY = feet_to_sm / 4.0  # Quarter mile


def get_feet_from_miles(miles):
    """
    Given miles, how many feet?

    Arguments:
        miles {float} -- The number of miles.

    Returns:
        float -- The number of feet.
    """

    return miles * feet_to_sm


def get_meters_from_feet(feet):
    """
    Returns meters from feet.

    Arguments:
        feet {float} -- The measurement in feet.

    Returns:
        [type] -- [description]
    """

    return feet / feet_to_m


def get_feet_from_meters(meters):
    """
    Returns feet from meters.

    Arguments:
        meters {float} -- The value in meters.

    Returns:
        float -- The meters converted to feet.
    """

    return meters * feet_to_m


def get_meters_per_second_from_mph(speed):
    """
    Given MPH, return meters/second

    Arguments:
        speed {float} -- Speed in MPH

    Returns:
        {float} -- Speed in meters/second
    """

    return mph_to_ms * speed


def get_converted_units_string(units, distance, unit_type=DISTANCE):
    if units is None:
        units = STATUTE

    if units != METRIC:
        if distance < IMPERIAL_NEARBY and unit_type != SPEED:
            return "{0:.0f}".format(distance) + "'"

        if units == NAUTICAL:
            return "{0:.1f}{1}".format(distance / feet_to_nm, UNIT_LABELS[NAUTICAL][unit_type])

        return "{0:.1f}{1}".format(distance / feet_to_sm, UNIT_LABELS[STATUTE][unit_type])
    else:
        conversion = distance / feet_to_km

        if conversion < 0.5 and units != SPEED:
            return "{0:.1f}{1}".format(conversion,  UNIT_LABELS[METRIC][unit_type])

        return "{0:.1f}m".format(distance / feet_to_m)

    return "{0:.0f}'".format(distance)
