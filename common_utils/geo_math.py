"""
Module for handling math around coordinates
"""

import math

EARTH_RADIUS_NAUTICAL_MILES = 3440
EARTH_RADIUS_STATUTE_MILES = 3959
EARTH_RADIUS_KILOMETERS_MILES = 6371


def get_bearing(
    starting_pos: list,
    ending_pos: list
) -> float:
    """
    Returns the bearing to the second GPS coord from the first.

    This is the initial great-circle bearing: the true course to fly
    when setting off. Over long distances it changes along the way.

    Arguments:
        starting_pos {(float,float)} -- The starting lat/long
        ending_pos {(float,float)} -- The ending lat/long

    Returns:
        float -- The bearing to lat2/lon2, in true degrees, 0 <= bearing < 360

    The four cardinal directions:

    >>> get_bearing([0, 0], [1, 0])
    0.0
    >>> get_bearing([0, 0], [0, 1])
    90.0
    >>> get_bearing([0, 0], [-1, 0])
    180.0
    >>> get_bearing([0, 0], [0, -1])
    270.0

    Just either side of north wraps correctly, not to 0:

    >>> round(get_bearing([0, 0], [1, 0.01]), 2)
    0.57
    >>> round(get_bearing([0, 0], [1, -0.01]), 2)
    359.43

    The same point has no direction; 0 is returned:

    >>> get_bearing([47.5, -122.2], [47.5, -122.2])
    0.0

    Real routes (great-circle initial courses):

    >>> round(get_bearing([47.5, -122.2], [44.0, -88.5]), 1)  # KAWO to KOSH
    86.0
    >>> round(get_bearing([47.4502, -122.3088], [45.5898, -122.5951]), 1)  # KSEA to KPDX
    186.1
    >>> round(get_bearing([40.6413, -73.7781], [33.9416, -118.4085]), 1)  # KJFK to KLAX
    273.8
    >>> round(get_bearing([33.9416, -118.4085], [40.6413, -73.7781]), 1)  # KLAX to KJFK
    65.9

    Heading "east" along 60N starts slightly left of 090, since the
    great circle bends toward the pole:

    >>> round(get_bearing([60, 0], [60, 1]), 1)
    89.6

    Across the antimeridian (180 degrees longitude):

    >>> round(get_bearing([0, 179.5], [0, -179.5]), 1)
    90.0
    >>> round(get_bearing([0, -179.5], [0, 179.5]), 1)
    270.0
    """
    lat = starting_pos[0]
    lon = starting_pos[1]

    lat2 = ending_pos[0]
    lon2 = ending_pos[1]

    teta1 = math.radians(lat)
    teta2 = math.radians(lat2)
    delta2 = math.radians(lon2-lon)

    y = math.sin(delta2) * math.cos(teta2)
    x = math.cos(teta1)*math.sin(teta2) - math.sin(teta1)*math.cos(teta2)*math.cos(delta2)
    brng = math.atan2(y, x)
    brng = math.degrees(brng)

    # atan2 gives -180..180; wrap the exact value into 0..360. (Any
    # rounding is left to whoever displays it.)
    return (brng + 360.0) % 360.0


def get_distance(
    starting_pos: list,
    ending_pos: list
) -> float:
    """
    Returns the great-circle distance between two points, treating
    the earth as a sphere (EARTH_RADIUS_STATUTE_MILES).

    Arguments:
        starting_pos {(float,float)} -- The starting lat/long
        ending_pos {(float,float)} -- The ending lat/long

    Returns:
        float -- The distance in STATUTE MILES between the given GPS points.

    One degree of latitude, or of longitude on the equator, is about
    69.1 statute miles (60 nautical miles):

    >>> round(get_distance([0, 0], [1, 0]), 2)
    69.1
    >>> round(get_distance([0, 0], [0, 1]), 2)
    69.1
    >>> round(get_distance([47.0, -122.0], [48.0, -122.0]), 2)
    69.1

    A degree of longitude shrinks with latitude; at 60N it is half:

    >>> round(get_distance([60, 0], [60, 1]), 2)
    34.55

    It doesn't matter which way you go:

    >>> get_distance([47.5, -122.2], [44.0, -88.5]) == get_distance([44.0, -88.5], [47.5, -122.2])
    True

    The same point is no distance:

    >>> get_distance([47.5, -122.2], [47.5, -122.2])
    0.0

    Real routes:

    >>> round(get_distance([47.4502, -122.3088], [45.5898, -122.5951]))  # KSEA to KPDX
    129
    >>> round(get_distance([40.6413, -73.7781], [33.9416, -118.4085]))  # KJFK to KLAX
    2470

    Across the antimeridian is the short way, not around the world:

    >>> round(get_distance([0, 179.5], [0, -179.5]), 2)
    69.1

    The farthest apart two points can be is half way around:

    >>> round(get_distance([0, 0], [0, 180]))
    12438
    """

    lat1 = starting_pos[0]
    lon1 = starting_pos[1]

    lat2 = ending_pos[0]
    lon2 = ending_pos[1]

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth. Can change with units
    r = EARTH_RADIUS_STATUTE_MILES

    return c * r


if __name__ == '__main__':
    import doctest

    print("Starting tests.")

    doctest.testmod()

    print("Finished tests.")
