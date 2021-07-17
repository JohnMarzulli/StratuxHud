"""
Module for handling math around coordinates
"""

import math

EARTH_RADIUS_NAUTICAL_MILES = 3440
EARTH_RADIUS_STATUTE_MILES = 3956
EARTH_RADIUS_KILOMETERS_MILES = 6371


def get_bearing(
    starting_pos: list,
    ending_pos: list
) -> float:
    """
    Returns the bearing to the second GPS coord from the first.

    Arguments:
        starting_pos {(float,float)} -- The starting lat/long
        ending_pos {(float,float)} -- The ending lat/long

    Returns:
        float -- The bearing to lat2/lon2
    """

    lat2 = starting_pos[0]
    lon2 = starting_pos[1]

    lat1 = ending_pos[0]
    lon1 = ending_pos[1]

    bearing = math.atan2(math.sin(lon2 - lon1) * math.cos(lat2), math.cos(lat1)
                         * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360

    return bearing


def get_distance(
    starting_pos: list,
    ending_pos: list
) -> float:
    """
    Returns the distance to the traffic from the given point.

    Arguments:
        starting_pos {(float,float)} -- The starting lat/long
        ending_pos {(float,float)} -- The ending lat/long

    Returns:
        float -- The distance in STATUTE MILES between the given GPS points.
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
