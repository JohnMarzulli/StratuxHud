"""
Common code for HUD view elements.
"""

from datetime import datetime

import pygame
from common_utils import fast_math, units
from configuration import configuration
from data_sources import ahrs_simulation, traffic
from data_sources.data_cache import HudDataCache
from rendering import colors, display

DEFAULT_FONT = "./assets/fonts/LiberationMono-Bold.ttf"

MAX_TARGET_BUGS = 25

IMPERIAL_FARAWAY = units.yards_to_sm * 5
IMPERIAL_SUPERCLOSE = units.yards_to_sm / 8.0

# pylint:disable=bare-except


def apply_declination(
    heading
) -> int:
    """
    Returns a heading to display with the declination adjust to convert from true to magnetic.

    Arguments:
        heading {float} -- The TRUE heading.

    Returns:
        float -- The MAGNETIC heading.
    """

    try:
        declination_applied = heading - configuration.CONFIGURATION.get_declination()
        new_heading = int(declination_applied)
    except:
        # If the heading is the unknown '---' then the math wil fail.
        return heading

    new_heading = fast_math.wrap_degrees(new_heading)

    return new_heading


def get_reticle_size(
    distance: float,
    min_reticle_size: float = 0.05,
    max_reticle_size: float = 0.20
) -> float:
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

    if distance <= IMPERIAL_SUPERCLOSE:
        on_screen_reticle_scale = max_reticle_size
    elif distance >= IMPERIAL_FARAWAY:
        on_screen_reticle_scale = min_reticle_size
    else:
        delta = distance - IMPERIAL_SUPERCLOSE
        scale_distance = IMPERIAL_FARAWAY - IMPERIAL_SUPERCLOSE
        ratio = delta / scale_distance
        reticle_range = max_reticle_size - min_reticle_size

        on_screen_reticle_scale = min_reticle_size + \
            (reticle_range * (1.0 - ratio))

    return on_screen_reticle_scale


def get_heading_bug_x(
    heading: float,
    bearing: float,
    degrees_per_pixel: float
) -> int:
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
    delta = fast_math.wrap_degrees(delta)

    return int(delta * degrees_per_pixel)


def run_hud_element(
    element_type,
    use_detail_font: bool = True
):
    """
    Runs an AHRS based HUD element alone for testing purposes

    Arguments:
        element_type {type} -- The class to create.

    Keyword Arguments:
        use_detail_font {bool} -- Should the detail font be used. (default: {True})
    """

    simulated_traffic = [traffic.SimulatedTraffic(max_distance) for max_distance in range(100, 100000, 5000)]

    clock = pygame.time.Clock()

    __backpage_framebuffer__, screen_size = display.display_init()  # args.debug)
    __width__, __height__ = screen_size
    pygame.mouse.set_visible(False)

    pygame.font.init()

    font_size_std = int(__height__ / 10.0)
    font_size_detail = int(__height__ / 12.0)

    __font__ = pygame.font.Font(DEFAULT_FONT, font_size_std)
    __detail_font__ = pygame.font.Font(DEFAULT_FONT, font_size_detail)

    if use_detail_font:
        font = __detail_font__
    else:
        font = __font__

    __aircraft__ = ahrs_simulation.AhrsSimulation()

    __pixels_per_degree_y__ = (__height__ / configuration.CONFIGURATION.get_degrees_of_pitch()
                               ) * configuration.CONFIGURATION.get_pitch_degrees_display_scaler()

    hud_element = element_type(
        configuration.CONFIGURATION.get_degrees_of_pitch(),
        __pixels_per_degree_y__,
        font,
        (__width__, __height__))

    while True:
        for test_data in simulated_traffic:
            test_data.simulate()
            traffic.AdsbTrafficClient.TRAFFIC_MANAGER.handle_traffic_report(
                test_data.icao_address,
                test_data.to_json())

        HudDataCache.update_traffic_reports()

        orientation = __aircraft__.get_ahrs()
        orientation.utc_time = str(datetime.utcnow())
        __aircraft__.simulate()
        __backpage_framebuffer__.fill(colors.BLACK)
        hud_element.render(__backpage_framebuffer__, orientation)
        pygame.display.flip()
        clock.tick(60)
