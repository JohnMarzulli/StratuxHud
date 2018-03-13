import math
import pickle
import display
from heads_up_display import HeadsUpDisplay

__sin_radians_by_degrees__ = {}
__cos_radians_by_degrees__ = {}

__width__ = 800
__height__ = 480
__screen_size__ = (__width__, __height__)
__center__ = (__screen_size__[0] >> 1, __screen_size__[1] >> 1 )
__long_line_width__ = __width__ * 0.2
__short_line_width__ = __width__ * 0.1
__pixels_per_degree_y__ = (__height__ / HeadsUpDisplay.DEGREES_OF_PITCH) * HeadsUpDisplay.PITCH_DEGREES_DISPLAY_SCALER
__pitch_elements__ = {}
degrees_of_pitch = 90

saved_ah_filename = 'ah.pickle'

for degrees in range(-360, 361):
    radians = math.radians(degrees)
    __sin_radians_by_degrees__[degrees] = math.sin(radians)
    __cos_radians_by_degrees__[degrees] = math.cos(radians)

def __build_ah_lookup__():
    ah_lookup = {}
    for pitch in range(-90, 91, 1):
        print "{0}..".format(pitch)
        ah_lookup[pitch] = __build_lookup_for_pitch__(pitch)
    
    return ah_lookup

def __build_lookup_for_pitch__(pitch):
    ah_lookup = {}
    for roll in range(-90, 91, 1):
        ah_lookup[roll] = __build_lookup_for_pitch_and_roll__(pitch, roll)
    
    return ah_lookup

def __build_lookup_for_pitch_and_roll__(pitch, roll):
    ah_lookup = []
    for reference_angle in range(-degrees_of_pitch, degrees_of_pitch + 1, 10):
        line_coords, line_center = __get_line_coords__(pitch, roll, reference_angle)

        if line_center[1] < 0 or line_center[1] > __height__:
            continue

        ah_lookup.append((line_coords, line_center, reference_angle))
    
    return ah_lookup

def __get_line_coords__(pitch, roll, reference_angle):
    """
    Get the coordinate for the lines for a given pitch and roll.
    """

    if reference_angle == 0:
        length = __long_line_width__
    else:
        length = __short_line_width__
    
    pitch = int(pitch)
    roll = int(roll)

    ahrs_center_x, ahrs_center_y = __center__
    pitch_offset = __pixels_per_degree_y__ * \
        (-pitch + reference_angle)

    roll_delta = 90 - roll

    center_x = int(
        (ahrs_center_x - (pitch_offset * __cos_radians_by_degrees__[roll_delta])) + 0.5)
    center_y = int(
        (ahrs_center_y - (pitch_offset * __sin_radians_by_degrees__[roll_delta])) + 0.5)

    x_len = int((length * __cos_radians_by_degrees__[roll]) + 0.5)
    y_len = int((length * __sin_radians_by_degrees__[roll]) + 0.5)

    half_x_len = x_len >> 1
    half_y_len = y_len >> 1

    start_x = center_x - half_x_len
    end_x = center_x + half_x_len
    start_y = center_y + half_y_len
    end_y = center_y - half_y_len

    return [[int(start_x), int(start_y)], [int(end_x), int(end_y)]], (int(center_x), int(center_y))

if __name__ == '__main__':
    generated_ah = __build_ah_lookup__()

    with open(saved_ah_filename, 'wb') as handle:
        pickle.dump(generated_ah, handle, protocol=pickle.HIGHEST_PROTOCOL)

    with open(saved_ah_filename, 'rb') as handle:
        b = pickle.load(handle)