# https://www.omnicalculator.com/physics/free-fall-air-resistance
# https://keisan.casio.com/exec/system/1231475371
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

terminal_velocity = 60  # m/s
gravity = 9.80665  # m/s^2
drag_scalar = 0.6
DEFAULT_K = 0.0001 # 0.01

CLAMP_SPEED = 0.1 # The slowest M/S we are willing to do the math on.


def get_bearing(starting_pos, ending_pos):
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


def get_distance(starting_pos, ending_pos):
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
    r = configuration.EARTH_RADIUS_STATUTE_MILES

    return c * r


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
        float -- The number of seconds until the destination is reached.
    """

    if math.fabs(current_speed) < CLAMP_SPEED:
        current_speed = CLAMP_SPEED

    return distance / current_speed


def get_free_fall_time(meters, mass, k = DEFAULT_K):
    return math.sqrt(mass/(gravity * k)) * math.acosh(math.e ** ((meters * k)/mass))


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

    if altitude <= 0.0:
        return 0.0

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
    flour_sack_weight = 0.22
    flour_sack_k = 0.01

    for test_altitude in (0, 25, 100, 200, 250, 400):
        time_to_impact = get_time_to_impact(
            units.get_meters_from_yards(test_altitude))
        free_fall_time = get_free_fall_time(units.get_meters_from_yards(
            test_altitude), flour_sack_weight, flour_sack_k)

        print('-----------')
        print('INPUT          :{0}'.format(test_altitude))
        print('Time           :{0}'.format(time_to_impact))
        print('Free_fall      :{0}'.format(free_fall_time))

    altitude_feet = 250 # time in fall was about 6.5
    ground_speed_mph = 60  # MPH
    ground_speed_ms = units.get_meters_per_second_from_mph(ground_speed_mph)

    print(ground_speed_ms)

    target_center_position = (48.160464, -122.166409)
    runway_number_position = (48.155973, -122.157582)
    distance_miles = get_distance(
        target_center_position, runway_number_position)
    distance_meters = units.get_meters_from_yards(
        units.get_yards_from_miles(distance_miles))
    time_to_target = get_time_to_distance(distance_meters, ground_speed_ms)
    time_to_impact = get_time_to_impact(
        units.get_meters_from_yards(altitude_feet))
    time_until_drop = time_to_target - time_to_impact
    bearing_to_target = get_bearing(
        runway_number_position, target_center_position)

    print("Free_fall:{0}".format(get_free_fall_time(
        units.get_meters_from_feet(altitude_feet), flour_sack_weight, flour_sack_k)))
    print("Distance(miles):{0}".format(distance_miles))
    print("Distance(meters):{0}".format(distance_meters))
    print("Time to target:{0}".format(time_to_target))
    print("Time to impact:{0}".format(time_to_impact))
    print("Time until drop:{0}".format(time_until_drop))
    print("Distance(miles):{0}".format(distance_miles))
    print("Bearing to target:{0}".format(bearing_to_target))
