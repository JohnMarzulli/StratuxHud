"""
For converting units.
"""

STATUTE = "statute"
NAUTICAL = "knots"
METRIC = "metric"


feet_to_nm = 6076.12
feet_to_sm = 5280.0
feet_to_km = 3280.84
feet_to_m = 3.28084
mph_to_ms = 0.44704

IMPERIAL_NEARBY = feet_to_sm / 4.0 # Quarter mile

def get_meters_per_second_from_mph(speed):
    """
    Given MPH, return meters/second
    
    Arguments:
        speed {float} -- Speed in MPH
    
    Returns:
        {float} -- Speed in meters/second
    """

    return mph_to_ms * speed


def get_distance_string(units, distance):
        if units is None:
            units = STATUTE

        if units != METRIC:
            if distance < IMPERIAL_NEARBY:
                return "{0:.0f}".format(distance) + "'"

            if units == NAUTICAL:
                return "{0:.1f}NM".format(distance / feet_to_nm)

            return "{0:.1f}SM".format(distance / feet_to_sm)
        else:
            conversion = distance / feet_to_km

            if conversion > 0.5:
                return "{0:.1f}km".format(conversion)

            return "{0:.1f}m".format(distance / feet_to_m)

        return "{0:.0f}'".format(distance)