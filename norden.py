# https://www.omnicalculator.com/physics/free-fall-air-resistance
#
# Advance mode
# Altitude 60m
# cross section - 0.5m/2
# mass .2kg
# c/D 1
# medium density = 0.96

# https://www.youtube.com/watch?v=ZPaRFr_3g2k

# -altitude = (velocity_initial * time) + (0.5 * 9.8 * time^2)
#
# Take into account starting altitude
#    loop over in 0.1second intervals.
#    Assume terminal velocity

# NOTE - ALL UNITS ARE IN METERS

import math

import units
import configuration

terminal_velocity = 30  # m/s
gravity = 9.8  # m/s^2
drag_scalar = 0.7


def get_bearing(starting_lat, starting_lon, lat2, lon2):
    """
    Returns the bearing to the second GPS coord from the first.

    Arguments:
        starting_lat {float} -- The starting latitude.
        starting_lon {float} -- The starting longitude.
        lat2 {float} -- The destination latitude.
        lon2 {float} -- The destination longitude.

    Returns:
        float -- The bearing to lat2/lon2
    """

    bearing = math.atan2(math.sin(lon2 - starting_lon) * math.cos(lat2), math.cos(starting_lat)
                         * math.sin(lat2) - math.sin(starting_lat) * math.cos(lat2) * math.cos(lon2 - starting_lon))
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360

    return bearing


def get_distance(starting_lat, starting_lon, lat2, lon2):
    """
    Returns the distance to the traffic from the given point.

    starting_lat {float} -- The starting latitude.
        starting_lon {float} -- The starting longitude.
        lat2 {float} -- The destination latitude.
        lon2 {float} -- The destination longitude.

    Returns:
        float -- The distance in STATUTE MILES between the given GPS points.
    """

    lon1 = starting_lon
    lat1 = starting_lat

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth. Can change with units
    r = configuration.EARTH_RADIUS_STATUTE_MILES

    return c * r


def get_altitude(time):
    """
    Returns the amount of distance traveled in a free fall using terminal velocity

    Assumes this is the distance dropped (IE ground = 0)

    Arguments:
        time {float} -- The number of seconds to calculate the fall for.

    Returns:
        float -- The number of feet traveled in the given amount of time.
    """

    # https://en.wikipedia.org/wiki/Free_fall#Uniform_gravitational_field_with_air_resistance

    altitude = ((terminal_velocity * terminal_velocity) / gravity) * \
        math.log1p(math.cosh((gravity * time) / terminal_velocity))

    return altitude


def get_distance_traveled(current_speed, time_slice):
    """
    Returns the distance traveled (single axis) in the given amount of time.

    Arguments:
        current_velocity {float} -- The current speed (meter/second). Single axis.
        time_slice {float} -- The amount of time to calculate for.

    Returns:
        [type] -- [description]
    """

    return current_speed * time_slice


def get_time_to_distance(distance, current_speed):
    """
    Returns the number of seconds to travel the distance.

    Assumes all metric units.

    Arguments:
        distance {float} -- The number of meters to the target.
        current_speed {float} -- The speed in meters per second.

    Returns:
        [type] -- [description]
    """

    return distance / current_speed


def get_time_to_impact(altitude, current_speed=0, total_time=0, time_slice=0.1):
    """
    Attempts to figure out how long it will take for something to
    hit the ground.

    Assumes the ground is at 0.

    Arguments:
        altitude {float} -- The starting altitude (AGL). Assumes 0 is the ground.

    Keyword Arguments:
        current_speed {int} -- The starting speed downwards. (default: {0})
        total_time {int} -- The amount of time that has passed. (default: {0})
        time_slice {float} -- How much time to simulate. (default: {0.1})

    Returns:
        [type] -- [description]
    """

    # TODO - Figure out how to make terminal_velocity apply exponentially
    #        instead of having a linear velocity growth
    # ground = 0
    acceleration = (gravity * time_slice) * drag_scalar
    new_velocity = current_speed + acceleration

    if new_velocity > terminal_velocity:
        new_velocity = terminal_velocity

    remaining_altitude = altitude - \
        get_distance_traveled(new_velocity, time_slice)

    # print str(altitude) + "," + str(current_velocity) + "," + str(total_time)

    if remaining_altitude <= 0.0:
        return total_time + time_slice

    return get_time_to_impact(remaining_altitude, new_velocity, total_time + time_slice)


if __name__ == '__main__':
    for test_altitude in (0, 25, 50, 100, 200, 500):
        time_to_impact = get_time_to_impact(test_altitude)
        altitude = get_altitude(time_to_impact)

        print('-----------')
        print('INPUT: ' + str(test_altitude))
        print("Time:  " + str(time_to_impact))
        print("Alt:   " + str(altitude))

    altitude_feet = 200
    ground_speed_mph = 60  # MPH
    ground_speed_ms = units.get_meters_per_second_from_mph(ground_speed_mph)

    print(ground_speed_ms)
