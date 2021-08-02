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
    brng = ((int(brng) + 360) % 360)

    return brng


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


# Expected is around 85
#kawo = [47.5, -122.2]
#kosh = [44.0, -88.5]
#print(get_bearing_close(kawo, kosh))
#print(get_bearing(kawo, kosh))
