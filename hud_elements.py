"""
Common code for HUD view elements.
"""


import datetime
import math
import threading

import pygame

import units
import configuration
import traffic
import views.utils as utils

from lib.display import WHITE, BLACK, YELLOW, display_init
from lib.task_timer import TaskTimer
from traffic import AdsbTrafficClient, Traffic

SIN_RADIANS_BY_DEGREES = {}
COS_RADIANS_BY_DEGREES = {}

imperial_nearby = 3000.0
max_altitude_delta = 5000.0
max_target_bugs = 25
imperial_occlude = units.feet_to_sm * 5
imperial_faraway = units.feet_to_sm * 2
imperial_superclose = units.feet_to_sm / 4.0

# Fill the quick trig look up tables.
for degrees in range(-360, 361):
    radians = math.radians(degrees)
    SIN_RADIANS_BY_DEGREES[degrees] = math.sin(radians)
    COS_RADIANS_BY_DEGREES[degrees] = math.cos(radians)


def get_reticle_size(distance, min_reticle_size=0.05, max_reticle_size=0.20):
    """
    The the size of the reticle based on the distance of the target.

    Arguments:
        distance {float} -- The distance (feet) to the target.

    Keyword Arguments:
        min_reticle_size {float} -- The minimum size of the reticle. (default: {0.05})
        max_reticle_size {float} -- The maximum size of the reticle. (default: {0.20})

    Returns:
        float -- The size of the reticle (in proportion to the screen size.)
    """

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
    __CACHE_ENTRY_LAST_USED__ = {}
    __CACHE_INVALIDATION_TIME__ = 60 * 5

    RELIABLE_TRAFFIC = []

    __LOCK__ = threading.Lock()

    @staticmethod
    def update_traffic_reports():
        HudDataCache.__LOCK__.acquire()
        HudDataCache.RELIABLE_TRAFFIC = traffic.AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()
        HudDataCache.__LOCK__.release()

    @staticmethod
    def get_reliable_traffic():
        """
        Returns a thread safe copy of the currently known reliable traffic.

        Returns:
            list -- A list of the reliable traffic.
        """
        HudDataCache.__LOCK__.acquire()
        traffic_clone = HudDataCache.RELIABLE_TRAFFIC[:]
        HudDataCache.__LOCK__.release()

        return traffic_clone

    @staticmethod
    def __purge_texture__(texture_to_purge):
        """
        Attempts to remove a texture from the cache.

        Arguments:
            texture_to_purge {string} -- The identifier of the texture to remove from the system.
        """

        try:
            del HudDataCache.TEXT_TEXTURE_CACHE[texture_to_purge]
            del HudDataCache.__CACHE_ENTRY_LAST_USED__[texture_to_purge]
        finally:
            return True

    @staticmethod
    def __get_purge_key__(now, texture_key):
        """
        Returns the key of the traffic to purge if it should be, otherwise returns None.

        Arguments:
            now {datetime} -- The current time.
            texture_key {string} -- The identifier of the texture we are interesting in.

        Returns:
            string -- The identifier to purge, or None
        """

        lsu = HudDataCache.__CACHE_ENTRY_LAST_USED__[texture_key]
        time_since_last_use = (datetime.datetime.utcnow() - lsu).total_seconds()

        return texture_key if time_since_last_use > HudDataCache.__CACHE_INVALIDATION_TIME__ else None

    @staticmethod
    def purge_old_traffic_reports():
        """
        Works through the traffic reports and removes any traffic that is
        old, or the cache has timed out on.
        """

        # The second hardest problem in comp-sci...
        textures_to_purge = []
        HudDataCache.__LOCK__.acquire()
        try:
            now = datetime.datetime.utcnow()
            textures_to_purge = [HudDataCache.__get_purge_key__(now, texture_key)
                                 for texture_key in HudDataCache.__CACHE_ENTRY_LAST_USED__]
            textures_to_purge = filter(lambda x: x is not None,
                                       textures_to_purge)
            [HudDataCache.__purge_texture__(texture_to_purge)
             for texture_to_purge in textures_to_purge]
        finally:
            HudDataCache.__LOCK__.release()

    @staticmethod
    def get_cached_text_texture(text, font, text_color=BLACK, background_color=YELLOW, use_alpha=False, force_regen=False):
        """
        Retrieves a cached texture.
        If the texture with the given text does not already exists, creates it.
        Uses only the text has the key. If the colors change, the cache is not invalidated or changed.

        Arguments:
            text {string} -- The text to generate a texture for.
            font {pygame.font} -- The font to use for the texture.

        Keyword Arguments:
            text_color {tuple} -- The RGB color for the text. (default: {BLACK})
            background_color {tuple} -- The RGB color for the BACKGROUND. (default: {YELLOW})
            use_alpha {bool} -- Should alpha be used? (default: {False})

        Returns:
            [tuple] -- The texture and the size of the texture
        """

        result = None
        HudDataCache.__LOCK__.acquire()
        try:
            if text not in HudDataCache.TEXT_TEXTURE_CACHE or force_regen:
                texture = font.render(text, True, text_color, background_color)
                size = texture.get_size()

                if use_alpha:
                    texture = texture.convert()

                HudDataCache.TEXT_TEXTURE_CACHE[text] = texture, size

            HudDataCache.__CACHE_ENTRY_LAST_USED__[text] = datetime.datetime.utcnow()
            result = HudDataCache.TEXT_TEXTURE_CACHE[text]
        finally:
            HudDataCache.__LOCK__.release()
        
        return result

def get_heading_bug_x(heading, bearing, degrees_per_pixel):
    """
    Gets the X position of a heading bug. 0 is the LHS.

    Arguments:
        heading {float} -- The current heading of the plane
        bearing {float} -- The bearing of the target.
        degrees_per_pixel {float} -- The number of degrees per horizontal pixel.

    Returns:
        int -- The screen X position.
    """

    delta = (bearing - heading + 180)
    if delta < 0:
        delta += 360

    if delta > 360:
        delta -= 360

    return int(delta * degrees_per_pixel)


def get_onscreen_traffic_projection__(heading, pitch, roll, bearing, distance, altitude_delta, pixels_per_degree):
    """
    Attempts to figure out where the traffic reticle should be rendered.
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


def run_ahrs_hud_element(element_type, use_detail_font=True):
    """
    Runs an AHRS based HUD element alone for testing purposes

    Arguments:
        element_type {type} -- The class to create.

    Keyword Arguments:
        use_detail_font {bool} -- Should the detail font be used. (default: {True})
    """

    from heads_up_display import HeadsUpDisplay
    from aircraft import AhrsSimulation
    from datetime import datetime

    clock = pygame.time.Clock()

    __backpage_framebuffer__, screen_size = display_init()  # args.debug)
    __width__, __height__ = screen_size
    pygame.mouse.set_visible(False)

    pygame.font.init()

    font_size_std = int(__height__ / 10.0)
    font_size_detail = int(__height__ / 12.0)

    __font__ = pygame.font.Font(
        "./assets/fonts/LiberationMono-Bold.ttf", font_size_std)
    __detail_font__ = pygame.font.Font(
        "./assets/fonts/LiberationMono-Bold.ttf", font_size_detail)

    if use_detail_font:
        font = __detail_font__
    else:
        font = __font__

    __aircraft__ = AhrsSimulation()

    __pixels_per_degree_y__ = (__height__ / configuration.CONFIGURATION.get_degrees_of_pitch()
                               ) * configuration.CONFIGURATION.get_pitch_degrees_display_scaler()

    hud_element = element_type(configuration.CONFIGURATION.get_degrees_of_pitch(),
                               __pixels_per_degree_y__, font, (__width__, __height__))

    while True:
        orientation = __aircraft__.ahrs_data
        orientation.utc_time = str(datetime.utcnow())
        __aircraft__.simulate()
        __backpage_framebuffer__.fill(BLACK)
        hud_element.render(__backpage_framebuffer__, orientation)
        pygame.display.flip()
        clock.tick(60)


def run_adsb_hud_element(element_type, use_detail_font=True):
    """
    Runs a ADSB based HUD element alone for testing purposes

    Arguments:
        element_type {type} -- The class to create.

    Keyword Arguments:
        use_detail_font {bool} -- Should the detail font be used. (default: {True})
    """

    from heads_up_display import HeadsUpDisplay
    from hud_elements import HudDataCache
    from aircraft import AhrsSimulation
    from traffic import SimulatedTraffic

    simulated_traffic = (SimulatedTraffic(),
                         SimulatedTraffic(), SimulatedTraffic())

    clock = pygame.time.Clock()

    __backpage_framebuffer__, screen_size = display_init()  # args.debug)
    __width__, __height__ = screen_size
    pygame.mouse.set_visible(False)

    pygame.font.init()

    font_size_std = int(__height__ / 10.0)
    font_size_detail = int(__height__ / 12.0)

    __font__ = pygame.font.Font(
        "./assets/fonts/LiberationMono-Bold.ttf", font_size_std)
    __detail_font__ = pygame.font.Font(
        "./assets/fonts/LiberationMono-Bold.ttf", font_size_detail)

    if use_detail_font:
        font = __detail_font__
    else:
        font = __font__

    __aircraft__ = AhrsSimulation()

    __pixels_per_degree_y__ = (__height__ / configuration.CONFIGURATION.get_degrees_of_pitch()) * \
        configuration.CONFIGURATION.get_pitch_degrees_display_scaler()

    hud_element = element_type(configuration.CONFIGURATION.get_degrees_of_pitch(),
                               __pixels_per_degree_y__, font,
                               (__width__, __height__))

    while True:
        for test_data in simulated_traffic:
            test_data.simulate()
            AdsbTrafficClient.TRAFFIC_MANAGER.handle_traffic_report(
                test_data.to_json())

        HudDataCache.purge_old_traffic_reports()
        orientation = __aircraft__.ahrs_data
        __aircraft__.simulate()
        __backpage_framebuffer__.fill(BLACK)
        hud_element.render(__backpage_framebuffer__, orientation)
        pygame.display.flip()
        clock.tick(60)


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
        print("TRUE: {0} -> {1} MAG".format(bearing,
                                            utils.apply_declination(bearing)))
