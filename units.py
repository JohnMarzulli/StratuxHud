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

    >>> get_feet_from_miles(0)
    0.0
    >>> get_feet_from_miles(1)
    5280.0
    >>> get_feet_from_miles(2)
    10560.0
    """

    if miles <= 0.0:
        return 0.0

    return miles * feet_to_sm


def get_meters_from_feet(feet):
    """
    Returns meters from feet.

    Arguments:
        feet {float} -- The measurement in feet.

    Returns:
        [type] -- [description]

    >>> get_meters_from_feet(0)
    0.0
    >>> get_meters_from_feet(1)
    0.3047999902464003
    >>> get_meters_from_feet(2)
    0.6095999804928006
    >>> get_meters_from_feet(3)
    0.914399970739201
    >>> get_meters_from_feet(100)
    30.47999902464003
    """

    if feet <= 0:
        return 0.0

    return feet / feet_to_m


def get_feet_from_meters(meters):
    """
    Returns feet from meters.

    Arguments:
        meters {float} -- The value in meters.

    Returns:
        float -- The meters converted to feet.

    >>> get_feet_from_meters(0)
    0.0
    >>> get_feet_from_meters(0.3047999902464003)
    1.0
    >>> get_feet_from_meters(0.6095999804928006)
    2.0
    >>> get_feet_from_meters(0.914399970739201)
    3.0
    >>> get_feet_from_meters(30.47999902464003)
    100.0
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
    """
    Given a base measurement (RAW from the ADS-B), a type of unit,
    and if it is speed or distance, returns a nice string for display.
    
    Arguments:
        units {string} -- 'statute', 'knots', or 'metric'
        distance {float} -- The raw measurement from the ADS-B receiver (feet).
    
    Keyword Arguments:
        unit_type {string} -- 'speed' or 'distance' (default: {DISTANCE})
    
    Returns:
        string -- A string for display in the given units and type.

    >>> get_converted_units_string('statute', 0, DISTANCE)
    "0'"
    >>> get_converted_units_string('statute', 0, SPEED)
    '0.0MPH'
    >>> get_converted_units_string('statute', 10, DISTANCE)
    "10'"
    >>> get_converted_units_string('statute', 5280, SPEED)
    '1.0MPH'
    >>> get_converted_units_string('statute', 528000, SPEED)
    '100.0MPH'
    """

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


if __name__ == '__main__':
    import doctest

    print("Starting tests.")

    doctest.testmod()

    print("Tests finished")
