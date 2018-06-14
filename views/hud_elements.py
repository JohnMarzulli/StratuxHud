import datetime
import math

import pygame

import aircraft
import display
import units
from configuration import DEFAULT_CONFIG_FILE, Configuration
from lib.task_timer import TaskTimer
from traffic import AdsbTrafficClient, Traffic

SIN_RADIANS_BY_DEGREES = {}
COS_RADIANS_BY_DEGREES = {}

imperial_nearby = 3000.0
imperial_occlude = units.feet_to_sm * 5
imperial_faraway = units.feet_to_sm * 2
imperial_superclose = units.feet_to_sm / 4.0

for degrees in range(-360, 361):
    radians = math.radians(degrees)
    SIN_RADIANS_BY_DEGREES[degrees] = math.sin(radians)
    COS_RADIANS_BY_DEGREES[degrees] = math.cos(radians)


def get_reticle_size(distance, min_reticle_size=0.05, max_reticle_size=0.20):
    on_screen_reticle_scale = min_reticle_size  # 0.05

    if distance <= imperial_superclose:
        on_screen_reticle_scale = max_reticle_size
    elif distance >= imperial_faraway:
        on_screen_reticle_scale = min_reticle_size
    else:
        delta = distance - imperial_superclose
        scale_distance = imperial_faraway - imperial_superclose
        ratio = delta / scale_distance
        reticle_range = max_reticle_size - min_reticle_size

        on_screen_reticle_scale = min_reticle_size + \
            (reticle_range * (1.0 - ratio))

    return on_screen_reticle_scale


class HudDataCache(object):
    TEXT_TEXTURE_CACHE = {}
    RELIABLE_TRAFFIC_REPORTS = []
    __CACHE_ENTRY_LAST_USED__ = {}
    __CACHE_INVALIDATION_TIME__ = 60 * 5

    @staticmethod
    def update_traffic_reports():
        HudDataCache.RELIABLE_TRAFFIC_REPORTS = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

        # The second hardest problem in comp-sci...
        textures_to_purge = []
        for texture_key in HudDataCache.__CACHE_ENTRY_LAST_USED__:
            lsu = HudDataCache.__CACHE_ENTRY_LAST_USED__[texture_key]
            time_since_last_use = (
                datetime.datetime.now() - lsu).total_seconds()
            if time_since_last_use > HudDataCache.__CACHE_INVALIDATION_TIME__:
                textures_to_purge.append(texture_key)

        for texture_to_purge in textures_to_purge:
            del HudDataCache.TEXT_TEXTURE_CACHE[texture_to_purge]
            del HudDataCache.__CACHE_ENTRY_LAST_USED__[texture_to_purge]

    @staticmethod
    def get_cached_text_texture(text, font):
        if text not in HudDataCache.TEXT_TEXTURE_CACHE:
            texture = font.render(
                text, True, display.BLACK, display.YELLOW)  # .convert()
            # text_width, text_height = texture.get_size()
            HudDataCache.TEXT_TEXTURE_CACHE[text] = texture  # , (
            # text_width, text_height)

        HudDataCache.__CACHE_ENTRY_LAST_USED__[text] = datetime.datetime.now()
        return HudDataCache.TEXT_TEXTURE_CACHE[text]


def get_heading_bug_x(heading, bearing, degrees_per_pixel):
    delta = (bearing - heading + 180)
    if delta < 0:
        delta += 360

    if delta > 360:
        delta -= 360

    return int(delta * degrees_per_pixel)


def get_onscreen_traffic_projection__(heading, pitch, roll, bearing, distance, altitude_delta, pixels_per_degree):
    """
    empts to figure out where the traffic reticle should be rendered.
    Returns value RELATIVE to the screen center.
    """

    # Assumes traffic.position_valid
    # TODO - Account for aircraft roll...
    slope = altitude_delta / distance
    vertical_degrees_to_target = math.degrees(math.atan(slope))
    vertical_degrees_to_target -= pitch

    # TODO - Double check ALL of this math...
    horizontal_degrees_to_target = bearing - heading

    screen_y = -vertical_degrees_to_target * pixels_per_degree
    screen_x = horizontal_degrees_to_target * pixels_per_degree

    return screen_x, screen_y


if __name__ == '__main__':
    for distance in range(0, int(2.5 * units.feet_to_sm), int(units.feet_to_sm / 10.0)):
        print("{0}' -> {1}".format(distance, get_reticle_size(distance)))

    heading = 327
    pitch = 0
    roll = 0
    distance = 1000
    altitude_delta = 1000
    pixels_per_degree = 10
    for bearing in range(0, 360, 10):
        print("Bearing {0} -> {1}px".format(bearing,
                                            get_heading_bug_x(heading, bearing, 2.2222222)))
        x, y = get_onscreen_traffic_projection__(
            heading, pitch, roll, bearing, distance, altitude_delta, pixels_per_degree)
        print("    {0}, {1}".format(x + 400, y + 240))
