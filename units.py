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

yards_to_nm = 2025.37
yards_to_sm = 1760.0
yards_to_km = 1093.61
yards_to_m = 1.09361
feet_to_nm = 6076.12
feet_to_sm = 5280.0
feet_to_km = 3280.84
feet_to_m = 3.28084
mph_to_ms = 0.44704

IMPERIAL_NEARBY = yards_to_sm / 4.0  # Quarter mile


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

    return miles * yards_to_sm


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

    return feet / yards_to_m


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

    return meters * yards_to_m


def get_meters_per_second_from_mph(speed):
    """
    Given MPH, return meters/second

    Arguments:
        speed {float} -- Speed in MPH

    Returns:
        {float} -- Speed in meters/second
    """

    return mph_to_ms * speed


def get_converted_units_string(units, distance, unit_type=DISTANCE, decimal_places=True):
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
    >>> get_converted_units_string('statute', 0.0, DISTANCE, True)
    "0'"
    >>> get_converted_units_string('statute', 0, SPEED, False)
    '0 MPH'
    >>> get_converted_units_string('statute', 0, SPEED, True)
    '0 MPH'
    >>> get_converted_units_string('statute', 10, DISTANCE)
    "10'"
    >>> get_converted_units_string('statute', 5280, SPEED)
    '1 MPH'
    >>> get_converted_units_string('statute', 5280, SPEED, False)
    '1 MPH'
    >>> get_converted_units_string('statute', 5280, SPEED, True)
    '1 MPH'
    >>> get_converted_units_string('statute', 5680, SPEED, True)
    '1 MPH'
    >>> get_converted_units_string('statute', 528000, SPEED)
    '100 MPH'
    """

    if units is None:
        units = STATUTE

    formatter_string = "{0:.1f}"
    formatter_no_decimals = "{0:.0f}"

    if not decimal_places or unit_type is SPEED:
        distance = int(distance)
        formatter_string = formatter_no_decimals

    with_units_formatter = formatter_string + " {1}"

    if units != METRIC:
        if distance < IMPERIAL_NEARBY and unit_type != SPEED:
            return formatter_no_decimals.format(distance) + "'"

        if units == NAUTICAL:
            return with_units_formatter.format(distance / yards_to_nm, UNIT_LABELS[NAUTICAL][unit_type])

        return with_units_formatter.format(distance / yards_to_sm, UNIT_LABELS[STATUTE][unit_type])
    else:
        conversion = distance / yards_to_km

        if conversion < 0.5 and units != SPEED:
            return with_units_formatter.format(conversion,  UNIT_LABELS[METRIC][unit_type])

        return with_units_formatter.format(distance / yards_to_m, "m")

    return with_units_formatter.format(distance, "ft")


if __name__ == '__main__':
    import doctest

    print("Starting tests.")

    doctest.testmod()

    print("Tests finished")
